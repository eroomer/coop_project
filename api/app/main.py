from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .schemas import AnalyzeRequest, AnalyzeResponse
from .stub_data import build_stub_result

app = FastAPI(
    title="3D Digital Twin AI API (Mock)",
    version="0.1.0",
    description="Mock server using keyword-based emergency detection.",
)

@app.get("/", response_class=HTMLResponse)
def index():
    # analyze 테스트 UI
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI API Mock UI</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; max-width: 760px; }
    label { display: block; margin-top: 12px; font-weight: 600; }
    input, textarea, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; }
    textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    button { cursor: pointer; margin-top: 14px; }
    pre { background: #0b1020; color: #e6e6e6; padding: 12px; border-radius: 12px; overflow: auto; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .hint { color: #555; font-size: 0.92rem; margin-top: 6px; }
  </style>
</head>
<body>
  <h2>API 서버입니다.</h2>

  <div class="card">
    <div class="row">
      <div>
        <label for="request_id">request_id</label>
        <input id="request_id" value="req-001" />
      </div>
      <div>
        <label for="image_id">image_id</label>
        <input id="image_id" value="fire_002.jpg" />
        <div class="hint">fire/smoke/accident 포함 시 high로 나옴(stub)</div>
      </div>
    </div>

    <label for="requested_at">requested_at</label>
    <input id="requested_at" />

    <label for="image_base64">image_base64</label>
    <textarea id="image_base64" rows="4" placeholder="base64 문자열 (테스트용으로 비워도 됨)"></textarea>

    <button onclick="sendAnalyze()">POST /v1/analyze 보내기</button>

    <label>Response</label>
    <pre id="out">{}</pre>

    <div class="hint">
      링크: <a href="/docs">/docs</a> · <a href="/redoc">/redoc</a> · <a href="/health">/health</a>
    </div>
  </div>

<script>
  // 페이지 로드시 requested_at 기본값 채우기
  document.getElementById("requested_at").value = new Date().toISOString();

  async function sendAnalyze() {
    const body = {
      request_id: document.getElementById("request_id").value,
      image_id: document.getElementById("image_id").value,
      image_base64: document.getElementById("image_base64").value || "stub",
      requested_at: document.getElementById("requested_at").value || new Date().toISOString()
    };

    const out = document.getElementById("out");
    out.textContent = "Loading...";

    try {
      const res = await fetch("/v1/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const text = await res.text();
      try {
        out.textContent = JSON.stringify(JSON.parse(text), null, 2);
      } catch {
        out.textContent = text;
      }
    } catch (e) {
      out.textContent = String(e);
    }
  }
</script>
</body>
</html>
"""

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    return build_stub_result(req.image_id)
