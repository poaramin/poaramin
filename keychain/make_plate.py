"""ป้ายทะเบียนรถจิ๋ว "รวย 888 เชียงใหม่" — สร้างไฟล์ STL/3MF สำหรับพิมพ์ 3D สองสี

ฐานป้ายสีขาว + ขอบ/ตัวอักษร สีดำ (นูนขึ้นจากฐาน) แบบป้ายรถยนต์ส่วนบุคคล
รัน:  python3 make_plate.py
"""
import numpy as np
import trimesh
from shapely.geometry import Point
from shapely.ops import unary_union

from bambu3mf import export_bambu_3mf
from make_keychain import BOLD, OUT, extrude, fit, rounded_rect, text_shape

# ---- ข้อความบนป้าย ----
LINE1 = "รวย"
LINE2 = "888"
PROVINCE = "เชียงใหม่"

# ---- ขนาด (มม.) — ป้าย 3 บรรทัด ----
W, H = 56.0, 42.0
CORNER = 2.5
BASE_T = 2.4               # ความหนาฐาน (ขาว)
RELIEF_T = 0.8             # ความสูงส่วนนูน (ดำ)
BORDER_INSET, BORDER_W = 1.2, 1.0


def build():
    # ---- ฐานขาว: แผ่นป้ายมุมมน (ไม่มีห่วง) ----
    base = rounded_rect(0, 0, W, H, CORNER)

    # ---- ส่วนดำ ----
    outer = rounded_rect(BORDER_INSET, BORDER_INSET, W - BORDER_INSET, H - BORDER_INSET,
                         CORNER - BORDER_INSET * 0.8)
    border = outer.difference(outer.buffer(-BORDER_W))

    # หมุดยึดป้ายสองข้าง (ตกแต่งเหมือนป้ายจริง)
    bolts = [Point(x, H - 5.0).buffer(0.9, quad_segs=12) for x in (6.0, W - 6.0)]

    l1 = fit(text_shape(LINE1, BOLD), W / 2, 32.0, W - 24, 9.0)
    l2 = fit(text_shape(LINE2, BOLD), W / 2, 19.5, W - 16, 10.0)
    prov = fit(text_shape(PROVINCE), W / 2, 6.8, 32, 6.8)

    black = unary_union([border, l1, l2, prov, *bolts]).intersection(base)
    return base, black, extrude(base, BASE_T), extrude(black, RELIEF_T, BASE_T)


def preview(base, black, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def patches(g, color):
        for p in getattr(g, "geoms", [g]):
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                c = list(ring.coords)
                verts += c
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
            yield PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    for pt in [*patches(base, "white"), *patches(black, "#111111")]:
        ax.add_patch(pt)
    ax.set_xlim(-2, W + 2)
    ax.set_ylim(-2, H + 2)
    ax.set_aspect("equal")
    ax.set_facecolor("#bfc5cc")
    ax.set_title(f"Mini license plate  {W:.0f} x {H:.0f} mm")
    fig.savefig(path, bbox_inches="tight")


def main():
    OUT.mkdir(exist_ok=True)
    base, black, white_m, black_m = build()
    white_m.visual.face_colors = [255, 255, 255, 255]
    black_m.visual.face_colors = [20, 20, 20, 255]
    white_m.export(OUT / "plate_base_white.stl")
    black_m.export(OUT / "plate_relief_black.stl")
    trimesh.util.concatenate([white_m, black_m]).export(OUT / "plate_single.stl")
    export_bambu_3mf(OUT / "plate_2color.3mf", "plate_รวย888",
                     [("base_white", white_m, "#FFFFFF"), ("relief_black", black_m, "#000000")])
    preview(base, black, OUT / "plate_preview.png")
    for name, m in [("white", white_m), ("black", black_m)]:
        print(f"{name}: watertight={m.is_watertight} bounds={np.round(m.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
