#!/usr/bin/env python3
import argparse
from pathlib import Path

from PIL import Image, ImageOps

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMG_EXTS


def letterbox(img: Image.Image, size: tuple[int, int], fill=(0, 0, 0)) -> Image.Image:
    """
    Resize while keeping aspect ratio, then pad to target size.
    """
    # Convert to RGB to avoid mode issues (e.g., RGBA/LA)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        # keep grayscale if you want; but RGB is safer for downstream models
        img = img.convert("RGB")

    target_w, target_h = size
    # ImageOps.contain keeps aspect ratio and fits within size
    img_resized = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)

    # Create background and paste centered
    background = Image.new("RGB", (target_w, target_h), fill)
    x = (target_w - img_resized.width) // 2
    y = (target_h - img_resized.height) // 2
    background.paste(img_resized, (x, y))
    return background


def stretch(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """
    Resize to target size without keeping aspect ratio (may distort).
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img.resize(size, resample=Image.Resampling.LANCZOS)


def process_dir(
    input_dir: Path,
    output_dir: Path,
    size: tuple[int, int],
    mode: str,
    overwrite: bool,
    fill: tuple[int, int, int],
    keep_ext: bool,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [p for p in input_dir.rglob("*") if p.is_file() and is_image(p)]
    if not files:
        print(f"[WARN] No images found in: {input_dir}")
        return

    ok, fail, skipped = 0, 0, 0
    for src in files:
        rel = src.relative_to(input_dir)
        dst_dir = output_dir / rel.parent
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Decide output extension
        out_ext = src.suffix.lower() if keep_ext else ".jpg"
        dst = (dst_dir / rel.stem).with_suffix(out_ext)

        if dst.exists() and not overwrite:
            skipped += 1
            continue

        try:
            with Image.open(src) as im:
                im = im.convert("RGB")  # normalize
                if mode == "letterbox":
                    out = letterbox(im, size=size, fill=fill)
                else:
                    out = stretch(im, size=size)

                # Save
                if dst.suffix.lower() in {".jpg", ".jpeg"}:
                    out.save(dst, quality=95, optimize=True)
                else:
                    out.save(dst)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"[FAIL] {src} -> {e}")

    print(f"[DONE] {input_dir} -> {output_dir} | ok={ok}, skipped={skipped}, fail={fail}")


def parse_rgb(s: str) -> tuple[int, int, int]:
    parts = s.split(",")
    if len(parts) != 3:
        raise ValueError("fill must be 'R,G,B' (e.g., 0,0,0)")
    return tuple(int(x) for x in parts)  # type: ignore


def main():
    ap = argparse.ArgumentParser(description="Unify dataset image sizes.")
    ap.add_argument("--input", required=True, help="Input dataset directory (e.g., datasets)")
    ap.add_argument("--output", required=True, help="Output directory (e.g., datasets_resized)")
    ap.add_argument("--size", default="640,640", help="Target size W,H (default: 640,640)")
    ap.add_argument("--mode", choices=["letterbox", "stretch"], default="letterbox",
                    help="letterbox keeps aspect ratio w/ padding, stretch distorts")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    ap.add_argument("--fill", default="0,0,0", help="Padding color for letterbox as R,G,B (default: 0,0,0)")
    ap.add_argument("--keep-ext", action="store_true", help="Keep original extension (default: convert to .jpg)")
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.split(","))
    size = (w, h)
    fill = parse_rgb(args.fill)

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")

    # Process base & emergency if present; otherwise process whole input dir
    base = input_dir / "base"
    emergency = input_dir / "emergency"
    if base.exists() or emergency.exists():
        if base.exists():
            process_dir(
                input_dir=base,
                output_dir=output_dir / "base",
                size=size,
                mode=args.mode,
                overwrite=args.overwrite,
                fill=fill,
                keep_ext=args.keep_ext,
            )
        if emergency.exists():
            process_dir(
                input_dir=emergency,
                output_dir=output_dir / "emergency",
                size=size,
                mode=args.mode,
                overwrite=args.overwrite,
                fill=fill,
                keep_ext=args.keep_ext,
            )
    else:
        process_dir(input_dir, output_dir, size, args.mode, args.overwrite, fill, args.keep_ext)


if __name__ == "__main__":
    main()
