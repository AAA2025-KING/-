(() => {
  const $ = (id) => document.getElementById(id);
  const brailleEl = $("braille");
  const contextEl = $("context");
  const backendEl = $("backend");
  const asTableEl = $("asTable");
  const resultEl = $("result");
  const metaEl = $("meta");
  const statusBox = $("statusBox");
  const btn = $("btnTranslate");
  const btnClear = $("btnClear");
  const btnPipeline = $("btnPipeline");
  const imageFile = $("imageFile");
  const tableWrap = $("tableWrap");
  const tableOut = $("tableOut");
  const mdOut = $("mdOut");
  const csvOut = $("csvOut");
  const cellPos = $("cellPos");
  const jumpRow = $("jumpRow");
  const jumpCol = $("jumpCol");
  const btnJump = $("btnJump");
  const btnSpeakCell = $("btnSpeakCell");
  const btnSpeakRow = $("btnSpeakRow");
  const btnSpeakTable = $("btnSpeakTable");
  const btnSpeakStop = $("btnSpeakStop");
  const ttsHint = $("ttsHint");

  /** @type {string[][]} */
  let tableCells = [];
  let selR = -1;
  let selC = -1;
  /** @type {SpeechSynthesisVoice | null} */
  let zhVoice = null;

  const ttsSupported = typeof window.speechSynthesis !== "undefined";

  function setStatus(text, kind) {
    statusBox.textContent = text;
    statusBox.className = "status" + (kind ? " " + kind : "");
  }

  function clearTable() {
    stopSpeak();
    tableWrap.classList.add("hidden");
    tableOut.innerHTML = "";
    mdOut.value = "";
    csvOut.value = "";
    tableCells = [];
    selR = -1;
    selC = -1;
    if (cellPos) cellPos.textContent = "点击或用方向键选择单元格";
  }

  function cellText(r, c) {
    if (!tableCells[r] || tableCells[r][c] == null) return "";
    return String(tableCells[r][c]);
  }

  function updateCellPos() {
    if (!cellPos) return;
    if (selR < 0 || selC < 0) {
      cellPos.textContent = "点击或用方向键选择单元格";
      return;
    }
    const text = cellText(selR, selC);
    cellPos.textContent =
      "第 " + (selR + 1) + " 行，第 " + (selC + 1) + " 列 · 内容：" + (text || "（空）");
    if (jumpRow) jumpRow.value = String(selR + 1);
    if (jumpCol) jumpCol.value = String(selC + 1);
  }

  function clearHighlights() {
    tableOut.querySelectorAll(".cbt-selected, .cbt-row-hl, .cbt-col-hl").forEach((el) => {
      el.classList.remove("cbt-selected", "cbt-row-hl", "cbt-col-hl");
    });
  }

  function selectCell(r, c, { focus = true } = {}) {
    if (!tableCells.length) return;
    const maxR = tableCells.length - 1;
    if (r < 0 || r > maxR) return;
    const maxC = (tableCells[r] || []).length - 1;
    if (maxC < 0 || c < 0 || c > maxC) return;
    selR = r;
    selC = c;
    clearHighlights();
    tableOut.querySelectorAll(".cbt-cell").forEach((el) => {
      const er = Number(el.getAttribute("data-r"));
      const ec = Number(el.getAttribute("data-c"));
      if (er === r) el.classList.add("cbt-row-hl");
      if (ec === c) el.classList.add("cbt-col-hl");
      if (er === r && ec === c) {
        el.classList.add("cbt-selected");
        if (focus) el.focus();
      }
    });
    updateCellPos();
  }

  function bindTableEvents() {
    const table = tableOut.querySelector("table");
    if (!table) return;
    table.setAttribute("role", "grid");
    tableOut.querySelectorAll(".cbt-cell").forEach((el) => {
      el.addEventListener("click", () => {
        selectCell(Number(el.getAttribute("data-r")), Number(el.getAttribute("data-c")));
      });
      el.addEventListener("keydown", (e) => {
        const r = Number(el.getAttribute("data-r"));
        const c = Number(el.getAttribute("data-c"));
        const rowLen = (tableCells[r] || []).length;
        let nr = r;
        let nc = c;
        if (e.key === "ArrowUp") {
          e.preventDefault();
          nr = Math.max(0, r - 1);
          nc = Math.min(c, (tableCells[nr] || []).length - 1);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          nr = Math.min(tableCells.length - 1, r + 1);
          nc = Math.min(c, (tableCells[nr] || []).length - 1);
        } else if (e.key === "ArrowLeft") {
          e.preventDefault();
          nc = Math.max(0, c - 1);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          nc = Math.min(rowLen - 1, c + 1);
        } else if (e.key === "Home") {
          e.preventDefault();
          nc = 0;
        } else if (e.key === "End") {
          e.preventDefault();
          nc = rowLen - 1;
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectCell(r, c);
          return;
        } else {
          return;
        }
        selectCell(nr, nc);
      });
    });
  }

  function ensureCellAttrsFromCells() {
    // If server HTML lacked data-r/c (old process), rebuild from cells array.
    if (tableOut.querySelector(".cbt-cell[data-r]")) return;
    if (!tableCells.length) return;
    const parts = ['<table class="cbt-table">'];
    tableCells.forEach((row, i) => {
      const tag = i === 0 ? "th" : "td";
      const cellsHtml = row
        .map((c, j) => {
          const esc = String(c)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
          return (
            "<" +
            tag +
            ' class="cbt-cell" data-r="' +
            i +
            '" data-c="' +
            j +
            '" tabindex="0">' +
            esc +
            "</" +
            tag +
            ">"
          );
        })
        .join("");
      parts.push("<tr>" + cellsHtml + "</tr>");
    });
    parts.push("</table>");
    tableOut.innerHTML = parts.join("\n");
  }

  function showTable(table) {
    if (!table || (!table.html && !(table.cells && table.cells.length))) {
      clearTable();
      return;
    }
    stopSpeak();
    tableWrap.classList.remove("hidden");
    tableCells = Array.isArray(table.cells)
      ? table.cells.map((row) => (Array.isArray(row) ? row.map((c) => String(c ?? "")) : []))
      : [];
    tableOut.innerHTML = table.html || "";
    ensureCellAttrsFromCells();
    mdOut.value = table.markdown || "";
    csvOut.value = table.csv || "";
    bindTableEvents();
    selR = -1;
    selC = -1;
    updateCellPos();
    if (tableCells.length && (tableCells[0] || []).length) {
      selectCell(0, 0, { focus: false });
    }
  }

  function pickZhVoice() {
    if (!ttsSupported) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    const prefer =
      voices.find((v) => /zh-CN/i.test(v.lang)) ||
      voices.find((v) => /zh[-_]?Hans/i.test(v.lang)) ||
      voices.find((v) => /^zh/i.test(v.lang)) ||
      voices.find((v) => /Chinese|中文|普通话|国语/i.test(v.name)) ||
      null;
    zhVoice = prefer;
    return prefer;
  }

  if (ttsSupported) {
    pickZhVoice();
    window.speechSynthesis.onvoiceschanged = () => pickZhVoice();
    if (ttsHint) ttsHint.classList.add("hidden");
  } else {
    if (ttsHint) ttsHint.classList.remove("hidden");
    [btnSpeakCell, btnSpeakRow, btnSpeakTable, btnSpeakStop].forEach((b) => {
      if (b) b.disabled = true;
    });
  }

  function stopSpeak() {
    if (ttsSupported) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
  }

  function speakText(text, { onend } = {}) {
    if (!ttsSupported) return;
    const u = new SpeechSynthesisUtterance(text || "");
    u.lang = "zh-CN";
    u.rate = 0.95;
    const voice = zhVoice || pickZhVoice();
    if (voice) u.voice = voice;
    if (onend) u.onend = onend;
    window.speechSynthesis.speak(u);
  }

  function speakQueue(parts) {
    if (!ttsSupported || !parts.length) return;
    stopSpeak();
    let i = 0;
    const next = () => {
      if (i >= parts.length) return;
      const chunk = parts[i++];
      speakText(chunk, { onend: next });
    };
    next();
  }

  function speakCell() {
    if (selR < 0 || selC < 0) {
      metaEl.textContent = "请先选择一个单元格。";
      return;
    }
    const text = cellText(selR, selC) || "空";
    const announce =
      "第" + (selR + 1) + "行第" + (selC + 1) + "列，" + text;
    stopSpeak();
    speakText(announce);
  }

  function speakRow() {
    if (selR < 0) {
      metaEl.textContent = "请先选择一行中的单元格。";
      return;
    }
    const row = tableCells[selR] || [];
    const parts = row.map((c, j) => {
      const t = String(c || "").trim() || "空";
      return t;
    });
    speakQueue(parts.map((t, i) => (i === 0 ? t : "，" + t)));
  }

  function speakTable() {
    if (!tableCells.length) {
      metaEl.textContent = "没有可朗读的表格。";
      return;
    }
    const parts = [];
    tableCells.forEach((row, r) => {
      row.forEach((c, j) => {
        const t = String(c || "").trim() || "空";
        if (j === 0 && r > 0) {
          parts.push("。第" + (r + 1) + "行，" + t);
        } else if (j === 0) {
          parts.push("第" + (r + 1) + "行，" + t);
        } else {
          parts.push("，" + t);
        }
      });
    });
    speakQueue(parts);
  }

  function doJump() {
    const r = parseInt(jumpRow && jumpRow.value, 10);
    const c = parseInt(jumpCol && jumpCol.value, 10);
    if (!Number.isFinite(r) || !Number.isFinite(c) || r < 1 || c < 1) {
      metaEl.textContent = "请输入有效的行号与列号（从 1 开始）。";
      return;
    }
    selectCell(r - 1, c - 1);
  }

  async function refreshHealth() {
    try {
      const res = await fetch("/health", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const h = await res.json();
      const lines = [
        "服务: 正常",
        "CUDA: " + (h.cuda ? "可用" + (h.gpu_name ? " — " + h.gpu_name : "") : "不可用"),
        "OCR: " + (h.ocr_ready ? "就绪 (OpenCV)" : "未安装 (pip install opencv-python-headless numpy Pillow)"),
        "适配器就绪: " + (h.adapter_ready ? "是" : "否") +
          (h.adapter_path ? " (" + h.adapter_path + ")" : ""),
        "已加载到显存: " + (h.adapter_loaded ? "是" : "否（首次翻译时加载）"),
      ];
      if (h.stub) lines.push("模式: CBT_QWEN_STUB=1（脚手架，不加载真模型）");
      setStatus(lines.join("\n"), h.cuda || h.stub ? "ok" : "warn");
    } catch (err) {
      setStatus("无法连接 /health：" + err.message, "err");
    }
  }

  async function doTranslate() {
    const braille = (brailleEl.value || "").trim();
    if (!braille) {
      metaEl.textContent = "请先输入盲文。";
      brailleEl.focus();
      return;
    }
    btn.disabled = true;
    metaEl.textContent = "翻译中…（首次加载模型可能需要数十秒）";
    resultEl.value = "";
    clearTable();
    try {
      const payload = {
        braille,
        backend: backendEl.value || "qwen8b",
        as_table: !!asTableEl.checked,
      };
      const ctx = (contextEl.value || "").trim();
      if (ctx) payload.context = ctx;

      const res = await fetch("/v1/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "请求失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      resultEl.value = data.text || "";
      showTable(data.table);
      metaEl.textContent =
        "后端: " + (data.backend || "?") + " · 耗时 " + (data.elapsed_s ?? "?") + " 秒" +
        (data.table ? " · 已还原表格" : "");
      refreshHealth();
    } catch (err) {
      resultEl.value = "";
      metaEl.textContent = "错误: " + err.message;
      setStatus("翻译失败: " + err.message, "err");
    } finally {
      btn.disabled = false;
    }
  }

  async function doPipeline() {
    const file = imageFile.files && imageFile.files[0];
    if (!file) {
      metaEl.textContent = "请先选择图片文件。";
      imageFile.focus();
      return;
    }
    btnPipeline.disabled = true;
    metaEl.textContent = "识别并翻译中…（OCR + 首次加载模型可能较慢）";
    resultEl.value = "";
    clearTable();
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("backend", backendEl.value || "qwen8b");
      fd.append("as_table", asTableEl.checked ? "true" : "false");
      const ctx = (contextEl.value || "").trim();
      if (ctx) fd.append("context", ctx);

      const res = await fetch("/v1/pipeline", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "请求失败";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      if (data.braille) brailleEl.value = data.braille;
      resultEl.value = data.text || "";
      showTable(data.table);
      metaEl.textContent =
        "OCR: " + (data.ocr_method || "?") +
        " · 置信 " + (data.confidence ?? "?") +
        " · 后端: " + (data.backend || "?") +
        " · 耗时 " + (data.elapsed_s ?? "?") + " 秒";
      refreshHealth();
    } catch (err) {
      resultEl.value = "";
      metaEl.textContent = "错误: " + err.message;
      setStatus("识别失败: " + err.message, "err");
    } finally {
      btnPipeline.disabled = false;
    }
  }

  document.querySelectorAll(".chip").forEach((el) => {
    el.addEventListener("click", () => {
      brailleEl.value = el.getAttribute("data-br") || "";
      contextEl.value = el.getAttribute("data-ctx") || "";
      if (el.getAttribute("data-table") === "1") asTableEl.checked = true;
      resultEl.value = "";
      clearTable();
      metaEl.textContent = "已填入样例「" + el.textContent + "」，可点翻译。";
    });
  });

  btn.addEventListener("click", doTranslate);
  btnPipeline.addEventListener("click", doPipeline);
  btnClear.addEventListener("click", () => {
    brailleEl.value = "";
    contextEl.value = "";
    resultEl.value = "";
    metaEl.textContent = "";
    imageFile.value = "";
    clearTable();
    brailleEl.focus();
  });

  if (btnJump) btnJump.addEventListener("click", doJump);
  if (btnSpeakCell) btnSpeakCell.addEventListener("click", speakCell);
  if (btnSpeakRow) btnSpeakRow.addEventListener("click", speakRow);
  if (btnSpeakTable) btnSpeakTable.addEventListener("click", speakTable);
  if (btnSpeakStop) btnSpeakStop.addEventListener("click", stopSpeak);

  brailleEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      doTranslate();
    }
  });

  refreshHealth();
})();
