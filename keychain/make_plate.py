"""พวงกุญแจป้ายทะเบียนรถ "รวย 888 เชียงใหม่" — สร้างไฟล์ STL/3MF สำหรับพิมพ์ 3D สองสี

ฐานป้ายสีขาว + ขอบ/ตัวอักษร สีดำ (นูนขึ้นจากฐาน) แบบป้ายรถยนต์ส่วนบุคคล
รัน:  python3 make_plate.py
"""
import numpy as np
import trimesh
from shapely.geometry import Point, box
from shapely.ops import unary_union

from make_keychain import BOLD, OUT, extrude, fit, rounded_rect, text_shape

# ---- ข้อความบนป้าย ----
PLATE_TEXT = "รวย 888"
PROVINCE = "เชียงใหม่"

# ---- ขนาด (มม.) — สัดส่วนใกล้ป้ายจริง 34 x 15 ซม. ----
W, H = 64.0, 28.0
CORNER = 2.5
BASE_T = 2.4               # ความหนาฐาน (ขาว)
RELIEF_T = 0.8             # ความสูงส่วนนูน (ดำ)
BORDER_INSET, BORDER_W = 1.2, 1.0
TAB_R, HOLE_R = 4.5, 2.2   # หูห้อยและรูพวงกุญแจ


def build():
    # ---- ฐานขาว: ป้าย + หูห้อยกลางด้านบน, เจาะรู ----
    plate = rounded_rect(0, 0, W, H, CORNER)
    tab_c = (W / 2, H + TAB_R * 0.55)
    base = unary_union([plate, Point(tab_c).buffer(TAB_R, quad_segs=24),
                        box(W / 2 - TAB_R, H - 4, W / 2 + TAB_R, tab_c[1])])
    base = base.difference(Point(tab_c).buffer(HOLE_R, quad_segs=24))

    # ---- ส่วนดำ ----
    outer = rounded_rect(BORDER_INSET, BORDER_INSET, W - BORDER_INSET, H - BORDER_INSET,
                         CORNER - BORDER_INSET * 0.8)
    border = outer.difference(outer.buffer(-BORDER_W))
    ring = Point(tab_c).buffer(TAB_R - 0.9).difference(Point(tab_c).buffer(HOLE_R + 0.7))

    # หมุดยึดป้ายสองข้าง (ตกแต่งเหมือนป้ายจริง)
    bolts = [Point(x, H - 4.2).buffer(0.9, quad_segs=12) for x in (6.0, W - 6.0)]

    top = fit(text_shape(PLATE_TEXT, BOLD), W / 2, 17.0, W - 14, 13.0)
    prov = fit(text_shape(PROVINCE), W / 2, 6.4, 30, 6.8)

    black = unary_union([border, ring, top, prov, *bolts]).intersection(base)
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
    ax.set_ylim(-2, H + 10)
    ax.set_aspect("equal")
    ax.set_facecolor("#bfc5cc")
    ax.set_title(f"License-plate keychain  {W:.0f} x {H:.0f} mm")
    fig.savefig(path, bbox_inches="tight")


def main():
    OUT.mkdir(exist_ok=True)
    base, black, white_m, black_m = build()
    white_m.visual.face_colors = [255, 255, 255, 255]
    black_m.visual.face_colors = [20, 20, 20, 255]
    white_m.export(OUT / "plate_base_white.stl")
    black_m.export(OUT / "plate_relief_black.stl")
    trimesh.util.concatenate([white_m, black_m]).export(OUT / "plate_keychain_single.stl")
    trimesh.Scene({"base_white": white_m, "relief_black": black_m}).export(
        OUT / "plate_keychain_2color.3mf")
    preview(base, black, OUT / "plate_preview.png")
    for name, m in [("white", white_m), ("black", black_m)]:
        print(f"{name}: watertight={m.is_watertight} bounds={np.round(m.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
