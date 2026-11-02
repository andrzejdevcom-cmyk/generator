import io
import json
import re
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import trimesh

CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"


def safe_name(value):
    return re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)[:150] or "part"


def print_meshes(parts, bed_width=180):
    """Lay parts flat in rows; rows can span multiple physical print jobs."""
    x, y, row_height = 0, 0, 0
    result = []
    for part in parts:
        if not part.printable:
            continue
        mesh = part.mesh.copy()
        mesh.apply_translation(-mesh.bounds[0])
        w, h, _ = mesh.extents
        if x > 0 and x+w > bed_width:
            x, y, row_height = 0, y+row_height+8, 0
        mesh.apply_translation([x, y, 0])
        result.append((part, mesh))
        x += w+8
        row_height = max(row_height, h)
    return result


def stl_bytes(parts, bed_width=180):
    meshes = [m for _, m in print_meshes(parts, bed_width)]
    if not meshes:
        raise ValueError("Brak części do eksportu.")
    return trimesh.util.concatenate(meshes).export(file_type="stl")


def three_mf(parts, layout="assembly", bed_width=180, include_references=False):
    ET.register_namespace("", CORE)
    selected = [p for p in parts if p.printable or include_references]
    meshes = print_meshes(selected, bed_width) if layout == "print" else [(p, p.mesh) for p in selected]
    model = ET.Element(f"{{{CORE}}}model", {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "pl-PL"})
    ET.SubElement(model, f"{{{CORE}}}metadata", {"name": "Application"}).text = "3DAS Letter Maker"
    ET.SubElement(model, f"{{{CORE}}}metadata", {"name": "Title"}).text = "Układ do druku" if layout == "print" else "Złożenie"
    resources = ET.SubElement(model, f"{{{CORE}}}resources")
    colors = list(dict.fromkeys(p.color for p, _ in meshes))
    materials = ET.SubElement(resources, f"{{{CORE}}}basematerials", {"id": "1"})
    for color in colors:
        ET.SubElement(materials, f"{{{CORE}}}base", {"name": color, "displaycolor": color.upper()+"FF"})
    build = ET.SubElement(model, f"{{{CORE}}}build")
    for index, (part, mesh) in enumerate(meshes, start=10):
        obj = ET.SubElement(resources, f"{{{CORE}}}object", {"id": str(index), "type": "model", "name": part.name, "pid": "1", "pindex": str(colors.index(part.color))})
        element = ET.SubElement(obj, f"{{{CORE}}}mesh")
        vertices = ET.SubElement(element, f"{{{CORE}}}vertices")
        for x, y, z in mesh.vertices:
            ET.SubElement(vertices, f"{{{CORE}}}vertex", {"x": f"{x:.8f}", "y": f"{y:.8f}", "z": f"{z:.8f}"})
        triangles = ET.SubElement(element, f"{{{CORE}}}triangles")
        for a, b, c in mesh.faces:
            ET.SubElement(triangles, f"{{{CORE}}}triangle", {"v1": str(a), "v2": str(b), "v3": str(c)})
        ET.SubElement(build, f"{{{CORE}}}item", {"objectid": str(index)})
    types = ET.Element("Types", {"xmlns": CONTENT})
    ET.SubElement(types, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(types, "Default", {"Extension": "model", "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})
    rels = ET.Element("Relationships", {"xmlns": REL})
    ET.SubElement(rels, "Relationship", {"Id": "rel0", "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel", "Target": "/3D/3dmodel.model"})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, element in (("[Content_Types].xml", types), ("_rels/.rels", rels), ("3D/3dmodel.model", model)):
            z.writestr(name, ET.tostring(element, encoding="utf-8", xml_declaration=True))
    return buf.getvalue()


def project_zip(result):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for part in result.parts:
            if part.printable:
                mesh = part.mesh.copy()
                mesh.apply_translation(-mesh.bounds[0])
                z.writestr(safe_name(part.name)+".stl", mesh.export(file_type="stl"))
        z.writestr("ASSEMBLY.3mf", three_mf(result.parts))
        z.writestr("PRINT_LAYOUT.3mf", three_mf(result.parts, "print", result.project.printer[0]))
        if any(not p.printable for p in result.parts):
            z.writestr("REFERENCE_DO_NOT_PRINT.3mf", three_mf(result.parts, include_references=True))
        z.writestr("project.json", result.project.model_dump_json(indent=2))
        z.writestr("assembly.json", json.dumps({"units": "mm", "placements": [p.model_dump() for p in result.placements],
                                               "neon_paths": [p.model_dump() for p in result.paths],
                                               "parts": [p.info(False) for p in result.parts], "stats": result.stats}, ensure_ascii=False, indent=2))
        z.writestr("CZYTAJ.txt", "Jednostki: mm. STL: osobne części ułożone tyłem na stole.\n"
                   "ASSEMBLY.3mf: pozycje montażowe; PRINT_LAYOUT.3mf: wszystkie części w rzędach. Rozdziel zadania według stołu drukarki.\n"
                   "REFERENCE_DO_NOT_PRINT.3mf zawiera również zakupione LED/złączki — tylko kontrola montażu.\n"
                   "Kolory 3MF są podstawowymi materiałami Core, bez profilu AMS i ustawień slicera. STL nie zawiera materiałów.\n"
                   "Mocowania/prowadnice są integralną geometrią korpusu. Zatrzaski i faza Z nie są zaimplementowane.\n"
                   "Nie potwierdzono zgodności w OrcaSlicer/Bambu Studio ani fizycznego dopasowania. Najpierw wydrukuj test luzów.\n")
    return buf.getvalue()


def read_3mf(data):
    """Independent core-mesh round-trip reader used in geometry tests."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": CORE}
    meshes = []
    for obj in model.findall("m:resources/m:object", ns):
        vertices = [[float(v.attrib[a]) for a in ("x", "y", "z")] for v in obj.findall("m:mesh/m:vertices/m:vertex", ns)]
        faces = [[int(v.attrib[a]) for a in ("v1", "v2", "v3")] for v in obj.findall("m:mesh/m:triangles/m:triangle", ns)]
        meshes.append(trimesh.Trimesh(np.array(vertices), np.array(faces), process=True))
    return meshes
