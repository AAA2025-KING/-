"""Corrections JSONL + merge helpers (no GPU)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chinese_braille_toolkit import corrections as corr


def test_build_and_append(tmp_path, monkeypatch):
    user = tmp_path / "user_corrections.jsonl"
    monkeypatch.setattr(corr, "USER_CORRECTIONS", user)
    monkeypatch.setattr(corr, "DATA_DIR", tmp_path)

    rec = corr.build_correction_record(
        braille="⠌⠖ ⠇⠳",
        zh="赵六",
        pred="兆六",
        row=1,
        col=0,
        context="实验器材表",
    )
    assert rec["braille"] == "⠌⠖ ⠇⠳"
    assert rec["zh"] == "赵六"
    assert rec["source_pred"] == "兆六"
    assert rec["conversations"][0]["from"] == "system"
    assert "赵六" in rec["conversations"][2]["value"]

    info = corr.append_correction(rec, path=user)
    assert info["count"] == 1
    assert user.is_file()
    line = user.read_text(encoding="utf-8").strip()
    assert json.loads(line)["zh"] == "赵六"

    with pytest.raises(ValueError):
        corr.build_correction_record(braille="⠁", zh="兆六", pred="兆六")


def test_merge_dedupe(tmp_path, monkeypatch):
    train = tmp_path / "train.jsonl"
    user = tmp_path / "user.jsonl"
    err = tmp_path / "err.jsonl"
    out = tmp_path / "merged.jsonl"

    train.write_text(
        json.dumps(
            {"braille": "⠁", "zh": "一", "conversations": []},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    # duplicate of train + one new
    user.write_text(
        json.dumps({"braille": "⠁", "zh": "一"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"braille": "⠌⠖ ⠇⠳", "zh": "赵六"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    err.write_text("", encoding="utf-8")

    monkeypatch.setattr(corr, "TRAIN_TABLES", train)
    monkeypatch.setattr(corr, "USER_CORRECTIONS", user)
    monkeypatch.setattr(corr, "ERROR_CORRECTIONS", err)
    monkeypatch.setattr(corr, "MERGED_TRAIN", out)
    monkeypatch.setattr(corr, "DATA_DIR", tmp_path)

    r = corr.merge_into_train()
    assert r["merged"] == 2
    assert r["dupes_skipped"] == 1
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert { (x["braille"], x["zh"]) for x in rows } == {("⠁", "一"), ("⠌⠖ ⠇⠳", "赵六")}


def test_api_corrections_endpoints(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import apps.api_server as server

    user = tmp_path / "user_corrections.jsonl"
    train = tmp_path / "train.jsonl"
    err = tmp_path / "err.jsonl"
    merged = tmp_path / "merged.jsonl"
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    train.write_text(
        json.dumps({"braille": "⠃", "zh": "二"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    err.write_text("", encoding="utf-8")

    monkeypatch.setattr(corr, "USER_CORRECTIONS", user)
    monkeypatch.setattr(corr, "TRAIN_TABLES", train)
    monkeypatch.setattr(corr, "ERROR_CORRECTIONS", err)
    monkeypatch.setattr(corr, "MERGED_TRAIN", merged)
    monkeypatch.setattr(corr, "DATA_DIR", tmp_path)
    monkeypatch.setattr(corr, "OUTPUTS_DIR", out_dir)
    monkeypatch.setattr(corr, "RETRAIN_REQUEST", out_dir / "retrain_request.json")
    monkeypatch.setattr(corr, "RETRAIN_STATUS", out_dir / "retrain_status.json")
    monkeypatch.setattr(corr, "ROOT", tmp_path)

    # Also patch the module used inside api_server
    monkeypatch.setattr(server.corr_mod, "USER_CORRECTIONS", user)
    monkeypatch.setattr(server.corr_mod, "TRAIN_TABLES", train)
    monkeypatch.setattr(server.corr_mod, "ERROR_CORRECTIONS", err)
    monkeypatch.setattr(server.corr_mod, "MERGED_TRAIN", merged)
    monkeypatch.setattr(server.corr_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(server.corr_mod, "OUTPUTS_DIR", out_dir)
    monkeypatch.setattr(server.corr_mod, "RETRAIN_REQUEST", out_dir / "retrain_request.json")
    monkeypatch.setattr(server.corr_mod, "RETRAIN_STATUS", out_dir / "retrain_status.json")
    monkeypatch.setattr(server.corr_mod, "ROOT", tmp_path)

    client = TestClient(server.app)
    r = client.post(
        "/v1/corrections",
        json={"braille": "⠌⠖ ⠇⠳", "zh": "赵六", "pred": "兆六", "row": 1, "col": 0},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["count"] == 1

    s = client.get("/v1/corrections/stats")
    assert s.status_code == 200
    assert s.json()["user_corrections"] == 1

    m = client.post("/v1/corrections/merge", json={})
    assert m.status_code == 200
    assert m.json()["merged"] >= 2

    p = client.post("/v1/retrain/prepare", json={"max_steps": 40})
    assert p.status_code == 200
    prep = p.json()
    assert "commands" in prep
    assert "powershell_one_liner" in prep["commands"]
    assert (out_dir / "retrain_request.json").is_file()

    # retrain without env should 403
    bad = client.post("/v1/retrain", json={"dry_run": True})
    assert bad.status_code == 403
