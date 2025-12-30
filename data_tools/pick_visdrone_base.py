import random
import shutil
import csv
from pathlib import Path

# ==============================
# Paths (UPDATED)
# ==============================

# VisDrone 원본 데이터 (HOME 아래)
VISDRONE_ROOT = Path.home() / "VisDrone2019-DET-test-dev"
IMG_DIR = VISDRONE_ROOT / "images"
ANN_DIR = VISDRONE_ROOT / "annotations"

# 프로젝트 datasets (submodule)
PROJECT_ROOT = Path.home() / "coop_project"
OUT_DIR = PROJECT_ROOT / "datasets" / "base"
MANIFEST = PROJECT_ROOT / "datasets" / "manifest.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# VisDrone class IDs of interest
# ==============================
# 1 pedestrian, 2 people, 4 car, 5 van, 6 truck, 9 bus
PERSON_VEHICLE = {1, 2, 4, 5, 6, 9}

def parse_annotation(txt_path: Path):
    """
    Parse VisDrone annotation file.
    Returns:
        total_objs, pv_objs, avg_occlusion, avg_truncation
    """
    total = pv = 0
    occ_sum = trunc_sum = 0

    with txt_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 8:
                continue

            category = int(parts[5])
            trunc = int(parts[6])
            occ = int(parts[7])

            total += 1
            trunc_sum += trunc
            occ_sum += occ

            if category in PERSON_VEHICLE:
                pv += 1

    if total == 0:
        return 0, 0, 0.0, 0.0

    return total, pv, occ_sum / total, trunc_sum / total


# ==============================
# 1) Candidate filtering
# ==============================
candidates = []

for ann_file in ANN_DIR.glob("*.txt"):
    total, pv, occ_avg, trunc_avg = parse_annotation(ann_file)

    # 최소 조건: 사람/차량 1개 이상
    if pv == 0:
        continue

    # 너무 극단적인 장면 제외 (조절 가능)
    if total > 150:
        continue
    if occ_avg > 2.2:
        continue
    if trunc_avg > 1.8:
        continue

    img_file = IMG_DIR / f"{ann_file.stem}.jpg"
    if img_file.exists():
        candidates.append((img_file, total, pv))

print(f"[INFO] candidate images: {len(candidates)}")

if not candidates:
    raise RuntimeError(
        "No candidates found. Check images/ and annotations/ directories."
    )

# ==============================
# 2) Sample 50 images
# ==============================
random.seed(42)
picked = random.sample(candidates, k=50) if len(candidates) >= 50 else candidates

# ==============================
# 3) Copy images & update manifest
# ==============================
rows = []

for idx, (img_path, total, pv) in enumerate(picked, start=1):
    out_name = f"base_{idx:03d}{img_path.suffix.lower()}"
    out_path = OUT_DIR / out_name

    shutil.copy2(img_path, out_path)

    rows.append({
        "id": f"base_{idx:03d}",
        "relative_path": f"base/{out_name}",
        "category": "base",
        "priority": "normal",
        "source": "visdrone",
        "note": f"objs={total}, pv={pv}"
    })

write_header = not MANIFEST.exists()

with MANIFEST.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["id", "relative_path", "category", "priority", "source", "note"]
    )
    if write_header:
        writer.writeheader()
    writer.writerows(rows)

print(f"[DONE] Copied {len(rows)} images to: {OUT_DIR}")
print(f"[DONE] Manifest updated: {MANIFEST}")
