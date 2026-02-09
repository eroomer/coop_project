from __future__ import annotations

from app.ai.homography import HomographyMapper

# 테스트 실행 명령어: python app/test_homography.py


def main():

    # 1) 4점 대응점 정의
    #    src: 이미지 픽셀 좌표 (u,v)
    #    dst: 맵/월드 좌표 (x,y)
    src_pts = [
        (100, 100),  # top-left
        (500, 120),  # top-right
        (520, 400),  # bottom-right
        (120, 420),  # bottom-left
    ]

    dst_pts = [
        (0.0, 0.0),  # top-left
        (10.0, 0.0),  # top-right
        (10.0, 6.0),  # bottom-right
        (0.0, 6.0),  # bottom-left
    ]

    mapper = HomographyMapper(src_pts=src_pts, dst_pts=dst_pts)

    # 2) 테스트할 점들 변환
    test_points_uv = [
        (100, 100),  # 꼭짓점
        (310, 260),  # 내부
        (520, 400),  # 꼭짓점
    ]

    print("=== uv -> xy results ===")
    for u, v in test_points_uv:
        x, y = mapper.uv_to_xy(u, v)
        print(f"uv=({u:.1f},{v:.1f}) -> xy=({x:.3f},{y:.3f})")


if __name__ == "__main__":
    main()
