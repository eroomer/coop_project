from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime
import uuid

from .schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult
from .db import init_db, insert_image, insert_analysis, get_analysis
from .storage import save_image_bytes
from .ai_pipeline import AIPipeline

# (선택) homography 예제 적용하고 싶으면 켜기
from .homography import HomographyMapper

app = FastAPI(
    title="3D Digital Twin AI API",
    version="0.3.0-week3",
    description="Week3: sync AI pipeline + DB + local image storage + homography utility.",
)

pipeline = AIPipeline()

# 예제용 homography: 4점 하드코딩(데모용)
# src: 이미지 픽셀 좌표, dst: 가상 지도 좌표
# 실제론 UI/설정파일로 받으면 더 좋지만 3주차는 예제 수준이면 OK
HOMO = HomographyMapper(
    src_pts=[(0, 0), (640, 0), (640, 360), (0, 360)],
    dst_pts=[(0, 0), (64, 0), (64, 36), (0, 36)],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index():
    # 기존 UI 그대로 유지 (문구만 week3로 약간 수정)
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI API UI</title>
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
  <h2>API 서버입니다. (Week3: Sync AI + DB + Local Storage)</h2>

  <div class="card">
    <div class="row">
      <div>
        <label for="request_id">request_id</label>
        <input id="request_id" value="req-001" />
      </div>
      <div>
        <label for="image_id">image_id</label>
        <input id="image_id" value="fire_002.jpg" />
        <div class="hint">현재는 YOLO가 COCO 라벨 기반이라 fire/smoke/accident는 fine-tuning 필요할 수 있음</div>
      </div>
    </div>

    <label for="requested_at">requested_at</label>
    <input id="requested_at" />

    <label for="image_base64">image_base64</label>
    <textarea id="image_base64" rows="6" placeholder="base64 문자열 (테스트용으로 stub도 가능)"></textarea>

    <button onclick="sendAnalyze()">POST /v1/analyze 보내기</button>

    <label>Response</label>
    <pre id="out">{}</pre>

    <div class="hint">
      링크: <a href="/docs">/docs</a> · <a href="/redoc">/redoc</a> · <a href="/health">/health</a>
    </div>
  </div>

<script>
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
    return {"status": "ok", "version": app.version}

@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Week3 behavior:
      - decode base64 image
      - save to local storage
      - write DB (images, analyses)
      - run sync AI pipeline (YOLO->crop->BLIP2)
      - (optional) homography mapping for bbox centers (example-level)
    """
    try:
        out = pipeline.run_from_base64(req.image_base64)
        image_bytes = out["image_bytes"]
        objects = out["objects"]
        caption = out["caption"]
        risk_level = out["risk_level"]

        # 1) local save
        ext = ".jpg"
        if "." in req.image_id:
            ext_guess = "." + req.image_id.split(".")[-1].lower()
            if 1 < len(ext_guess) <= 8:
                ext = ext_guess

        image_path, digest = save_image_bytes(image_bytes, ext=ext)

        # 2) DB insert: images
        image_ref_id = insert_image(image_id=req.image_id, path=image_path, sha256=digest)

        # 3) (optional) homography: bbox 중심점에 (x,y) 추가 (예제)
        # schema를 바꾸지 않기 위해 objects 안에 "map_xy" 같은 추가 필드를 넣지 않고,
        # caption에 붙이거나 merged_json을 따로 두는 방식이 정석인데,
        # 현재 schemas에 merged 필드가 없으니 일단 "서버 내부 로그/추후 확장" 용도로만 계산해둠.
        for o in objects:
            bbox = o.get("bbox_xyxy")
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                uc = (x1 + x2) / 2.0
                vc = (y1 + y2) / 2.0
                mx, my = HOMO.uv_to_xy(uc, vc)
                # 스키마 불변 유지: 분석 저장용 objects에는 map_xy를 포함시켜도 DB엔 저장 가능
                # (Pydantic 응답에선 무시되도록 하려면 schemas에서 extra 허용이 필요하니,
                #  여기서는 DB 저장용만 복사본에 넣는 게 안전)
                o["_map_xy"] = [mx, my]

        # 4) DB insert: analyses
        analysis_id = insert_analysis(
            request_id=req.request_id,
            image_ref_id=image_ref_id,
            risk_level=risk_level,
            objects=objects,
            caption=caption,
        )

        # 5) response (schemas 준수: _map_xy 같은 extra 필드는 제거해서 반환)
        safe_objects = []
        for o in objects:
            safe_objects.append({
                "label": o.get("label", "unknown"),
                "confidence": float(o.get("confidence", 0.0)),
                "bbox_xyxy": o.get("bbox_xyxy"),
            })

        result = AnalyzeResult(
            result_id=str(analysis_id),
            image_id=req.image_id,
            risk_level=risk_level,  # "high" | "normal"
            objects=safe_objects,
            caption=caption,
        )

        return AnalyzeResponse(
            response_id=str(uuid.uuid4()),
            ok=True,
            result=result,
            error_code=None,
        )

    except Exception as e:
        return AnalyzeResponse(
            response_id=str(uuid.uuid4()),
            ok=False,
            result=None,
            error_code=f"INTERNAL_ERROR: {type(e).__name__}",
        )

@app.get("/v1/result/{analysis_id}")
def get_result(analysis_id: int):
    """
    DB 조회용 (Week3 산출물: DB 연동 확인을 위해 추가)
    """
    data = get_analysis(analysis_id)
    if data is None:
        return {"ok": False, "error_code": "NOT_FOUND"}
    return {"ok": True, "data": data}
