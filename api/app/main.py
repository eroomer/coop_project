from fastapi import FastAPI
from .schemas import AnalyzeRequest, AnalyzeResponse
from .stub_data import build_stub_result

app = FastAPI(
    title="3D Digital Twin AI API (Mock)",
    version="0.1.0",
    description="Mock server using keyword-based emergency detection.",
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    return build_stub_result(req.image_id)
