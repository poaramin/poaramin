"""เขียนไฟล์ 3MF ที่เปิดใน Bambu Studio แล้วมีสีพร้อม (แต่ละชิ้นผูกกับ filament ช่อง 1, 2, ...)

ชิ้นส่วนทั้งหมดรวมเป็น object เดียวหลาย part (ไม่ต้องตอบ dialog แยกชิ้น)
และใส่ basematerials/displaycolor ตามมาตรฐาน 3MF ไว้ให้สไลเซอร์อื่นด้วย
"""
import json
import zipfile
from xml.sax.saxutils import escape

BED_CENTER = (128.0, 128.0)  # กลางฐานพิมพ์ Bambu A1 (256 x 256 มม.)


def _mesh_xml(mesh, pid=None):
    v = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in mesh.vertices)
    p = f' pid="1" p1="{pid}"' if pid is not None else ""
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"{p}/>' for a, b, c in mesh.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def export_bambu_3mf(path, name, parts):
    """parts: list ของ (ชื่อ, trimesh, "#RRGGBB") — ลำดับในลิสต์ = filament ช่อง 1, 2, ..."""
    lo = min(m.bounds[0][0] for _, m, _ in parts), min(m.bounds[0][1] for _, m, _ in parts)
    hi = max(m.bounds[1][0] for _, m, _ in parts), max(m.bounds[1][1] for _, m, _ in parts)
    # วาง object ให้อยู่กลางฐานพิมพ์
    dx = BED_CENTER[0] - (lo[0] + hi[0]) / 2
    dy = BED_CENTER[1] - (lo[1] + hi[1]) / 2
    obj_id = len(parts) + 2

    mats = "".join(f'<base name="{escape(n)}" displaycolor="{c}FF"/>' for n, _, c in parts)
    objs = "".join(
        f'<object id="{i + 2}" type="model">{_mesh_xml(m, i)}</object>'
        for i, (_, m, _) in enumerate(parts))
    comps = "".join(f'<component objectid="{i + 2}"/>' for i in range(len(parts)))
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
        '<metadata name="Application">BambuStudio-01.09.00.00</metadata>'
        '<metadata name="BambuStudio:3mfVersion">1</metadata>'
        f'<resources><basematerials id="1">{mats}</basematerials>{objs}'
        f'<object id="{obj_id}" type="model"><components>{comps}</components></object>'
        '</resources>'
        f'<build><item objectid="{obj_id}" transform="1 0 0 0 1 0 0 0 1 {dx:.4f} {dy:.4f} 0" '
        'printable="1"/></build></model>')

    part_cfg = "".join(
        f'<part id="{i + 2}" subtype="normal_part">'
        f'<metadata key="name" value="{escape(n)}"/>'
        f'<metadata key="extruder" value="{i + 1}"/></part>'
        for i, (n, _, _) in enumerate(parts))
    settings = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>'
        f'<object id="{obj_id}"><metadata key="name" value="{escape(name)}"/>'
        f'<metadata key="extruder" value="1"/>{part_cfg}</object></config>')

    project = {"filament_colour": [c for _, _, c in parts],
               "filament_type": ["PLA"] * len(parts)}

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", settings)
        z.writestr("Metadata/project_settings.config", json.dumps(project, indent=2))
