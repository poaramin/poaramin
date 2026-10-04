"""พวงกุญแจป้ายทางหลวง "เชียงใหม่" — สร้างไฟล์ STL/3MF สำหรับพิมพ์ 3D สองสี

ฐานป้ายสีเขียว + ขอบ/ตัวอักษร/ลูกศร/โล่ทางหลวง สีขาว (นูนขึ้นจากฐาน)
รัน:  python3 make_keychain.py
"""
from pathlib import Path

import numpy as np
import trimesh
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "fonts" / "Kanit-SemiBold.ttf"
BOLD = HERE.parent / "fonts" / "Kanit-Bold.ttf"
OUT = HERE / "output"

# ---- ขนาด (มม.) ----
W, H = 60.0, 30.0          # ขนาดแผ่นป้าย
CORNER = 3.0               # รัศมีมุมโค้ง
BASE_T = 2.4               # ความหนาฐาน (เขียว)
RELIEF_T = 0.8             # ความสูงส่วนนูน (ขาว)
BORDER_INSET, BORDER_W = 1.2, 1.0
TAB_R, HOLE_R = 4.5, 2.2   # หูห้อยและรูพวงกุญแจ
ROUTE = "11"               # ทางหลวงหมายเลข 11 (อินทร์บุรี–เชียงใหม่)


class ShapelyPen(BasePen):
    """แปลง glyph outline เป็นรายการ ring (ประมาณเส้นโค้งด้วยจุด)"""

    def __init__(self, glyphset, steps=8):
        super().__init__(glyphset)
        self.rings, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            u = 1 - t
            self.cur.append(tuple(u**3 * np.array(p0) + 3 * u * u * t * np.array(p1)
                                  + 3 * u * t * t * np.array(p2) + t**3 * np.array(p3)))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            u = 1 - t
            self.cur.append(tuple(u * u * np.array(p0) + 2 * u * t * np.array(p1) + t * t * np.array(p2)))

    def _closePath(self):
        if len(self.cur) >= 3:
            self.rings.append(self.cur)
        self.cur = []

    _endPath = _closePath


def rings_to_shape(rings):
    """รวม contour ด้วยกฎ even-odd: ring ที่ซ้อนกันกลายเป็นรู"""
    shape = Polygon()
    for r in sorted(rings, key=lambda r: -abs(Polygon(r).area)):
        p = Polygon(r).buffer(0)
        shape = shape.symmetric_difference(p) if shape.intersects(p) else shape.union(p)
    return shape


def text_shape(text, font_path=FONT):
    """จัดรูปข้อความด้วย HarfBuzz (วรรณยุกต์/สระไทยวางถูกตำแหน่ง) แล้วคืน shapely geometry"""
    blob = hb.Blob.from_file_path(str(font_path))
    hbfont = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {})
    tt = TTFont(str(font_path))
    gs, order = tt.getGlyphSet(), tt.getGlyphOrder()
    parts, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = ShapelyPen(gs)
        gs[order[info.codepoint]].draw(pen)
        if pen.rings:
            parts.append(affinity.translate(rings_to_shape(pen.rings),
                                            x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    return unary_union(parts)


def fit(shape, cx, cy, max_w, max_h):
    """ย่อ/ขยายให้พอดีกรอบแล้ววางกึ่งกลางที่ (cx, cy)"""
    x0, y0, x1, y1 = shape.bounds
    s = min(max_w / (x1 - x0), max_h / (y1 - y0))
    shape = affinity.scale(shape, s, s, origin=(0, 0))
    x0, y0, x1, y1 = shape.bounds
    return affinity.translate(shape, cx - (x0 + x1) / 2, cy - (y0 + y1) / 2)


def rounded_rect(x0, y0, x1, y1, r):
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=16)


def up_arrow(cx, cy, h, w):
    """ลูกศรชี้ขึ้น (ตรงไป) แบบป้ายบอกทาง"""
    head_h, shaft_w = h * 0.45, w * 0.36
    pts = [(cx, cy + h / 2), (cx + w / 2, cy + h / 2 - head_h),
           (cx + shaft_w / 2, cy + h / 2 - head_h), (cx + shaft_w / 2, cy - h / 2),
           (cx - shaft_w / 2, cy - h / 2), (cx - shaft_w / 2, cy + h / 2 - head_h),
           (cx - w / 2, cy + h / 2 - head_h)]
    return Polygon(pts)


def shield(cx, cy, w, h):
    """โล่ทางหลวงแผ่นดิน (ทรงโล่ด้านบนตรง ด้านล่างแหลมมน)"""
    top = cy + h / 2
    t = np.linspace(0, np.pi, 40)
    bottom = [(cx + (w / 2) * np.cos(a), cy - h * 0.05 - (h * 0.45) * np.sin(a)) for a in t]
    return Polygon([(cx - w / 2, top), (cx + w / 2, top)] + bottom).buffer(0.4).buffer(-0.4)


def extrude(shape, height, z0=0.0):
    geoms = getattr(shape, "geoms", [shape])
    meshes = [trimesh.creation.extrude_polygon(g, height) for g in geoms if g.area > 0.01]
    m = trimesh.util.concatenate(meshes)
    m.apply_translation([0, 0, z0])
    return m


def build():
    # ---- ฐานเขียว: ป้าย + หูห้อยมุมซ้ายบน, เจาะรู ----
    plate = rounded_rect(0, 0, W, H, CORNER)
    tab_c = (TAB_R + 1.0, H + TAB_R * 0.55)
    base = unary_union([plate, Point(tab_c).buffer(TAB_R, quad_segs=24),
                        box(1.0, H - 4, 1.0 + 2 * TAB_R, tab_c[1])])
    base = base.difference(Point(tab_c).buffer(HOLE_R, quad_segs=24))

    # ---- ส่วนขาว ----
    outer = rounded_rect(BORDER_INSET, BORDER_INSET, W - BORDER_INSET, H - BORDER_INSET,
                         CORNER - BORDER_INSET)
    border = outer.difference(outer.buffer(-BORDER_W))
    # ขอบรอบรูพวงกุญแจ
    ring = Point(tab_c).buffer(TAB_R - 0.9).difference(Point(tab_c).buffer(HOLE_R + 0.7))

    arrow = up_arrow(8.0, H / 2, 17, 8.5)
    th = fit(text_shape("เชียงใหม่"), 30.0, 19.0, 28.5, 10.5)
    en = fit(text_shape("Chiang Mai"), 30.0, 8.0, 26, 5.0)

    # โล่ทางหลวง: โล่ขาว + เลขเว้นเป็นสีเขียว
    sh = shield(51.2, H / 2 + 0.5, 8.6, 11.0)
    num = fit(text_shape(ROUTE, BOLD), 51.2, H / 2 + 1.6, 5.6, 5.0)
    sh = sh.difference(num)

    white = unary_union([border, ring, arrow, th, en, sh]).intersection(base)

    green_m = extrude(base, BASE_T)
    white_m = extrude(white, RELIEF_T, BASE_T)
    return base, white, green_m, white_m


def preview(base, white, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def patch(g, color):
        for p in getattr(g, "geoms", [g]):
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                c = list(ring.coords)
                verts += c
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
            yield PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    for pt in patch(base, "#00704A"):
        ax.add_patch(pt)
    for pt in patch(white, "white"):
        ax.add_patch(pt)
    ax.set_xlim(-2, W + 2)
    ax.set_ylim(-2, H + 10)
    ax.set_aspect("equal")
    ax.set_facecolor("#d9d9d9")
    ax.set_title(f"Chiang Mai highway-sign keychain  {W:.0f} x {H:.0f} mm")
    fig.savefig(path, bbox_inches="tight")


def main():
    OUT.mkdir(exist_ok=True)
    base, white, green_m, white_m = build()
    green_m.visual.face_colors = [0, 112, 74, 255]
    white_m.visual.face_colors = [255, 255, 255, 255]
    green_m.export(OUT / "chiangmai_base_green.stl")
    white_m.export(OUT / "chiangmai_relief_white.stl")
    trimesh.util.concatenate([green_m, white_m]).export(OUT / "chiangmai_keychain_single.stl")
    from bambu3mf import export_bambu_3mf
    export_bambu_3mf(OUT / "chiangmai_keychain_2color.3mf", "chiangmai_keychain",
                     [("base_green", green_m, "#00704A"), ("relief_white", white_m, "#FFFFFF")])
    preview(base, white, OUT / "preview.png")
    for name, m in [("green", green_m), ("white", white_m)]:
        print(f"{name}: watertight={m.is_watertight} bounds={np.round(m.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
