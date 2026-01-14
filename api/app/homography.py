from __future__ import annotations
import numpy as np
import cv2

class HomographyMapper:
    """
    Example-level homography:
      src_pts (u,v) 4 points in image
      dst_pts (x,y) 4 points in map coordinates
    """
    def __init__(self, src_pts: list[tuple[float, float]], dst_pts: list[tuple[float, float]]):
        if len(src_pts) != 4 or len(dst_pts) != 4:
            raise ValueError("Need exactly 4 point correspondences (src=4, dst=4).")
        self.src = np.array(src_pts, dtype=np.float32)
        self.dst = np.array(dst_pts, dtype=np.float32)
        self.H = cv2.getPerspectiveTransform(self.src, self.dst)

    def uv_to_xy(self, u: float, v: float) -> tuple[float, float]:
        p = np.array([[[u, v]]], dtype=np.float32)  # (1,1,2)
        out = cv2.perspectiveTransform(p, self.H)   # (1,1,2)
        x, y = out[0, 0]
        return float(x), float(y)
