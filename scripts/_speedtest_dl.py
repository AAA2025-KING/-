import os, time, urllib.request
url = "https://hf-mirror.com/Violet-yo/Vision-Braille-Qwen3-8B/resolve/main/model-00001-of-00004.safetensors"
out = os.path.join(os.environ.get("TEMP", "/tmp"), "vb_test.bin")
print("GET", url, flush=True)
t0 = time.time()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=90) as resp:
    print("final_url", resp.geturl(), flush=True)
    print("status", getattr(resp, "status", None), "len", resp.headers.get("Content-Length"), flush=True)
    n = 0
    with open(out, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
            elapsed = time.time() - t0
            if n == chunk.__len__() or int(elapsed) % 5 == 0:
                print(f"prog mb={n/1024/1024:.2f} secs={elapsed:.1f}", flush=True)
            if elapsed >= 30:
                print(f"SAMPLE bytes={n} mb={n/1024/1024:.2f} secs={elapsed:.1f} speed_MBps={n/1024/1024/max(elapsed,0.01):.3f}", flush=True)
                break
print("done_sample path=", out, flush=True)
