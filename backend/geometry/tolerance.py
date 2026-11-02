import io
import zipfile

from shapely.geometry import box

from backend.export.files import three_mf
from backend.geometry.solids import Part, extrude, union


def tolerance_parts(project):
    parts = []
    for i, clearance in enumerate((.15, .25, .35, .45)):
        shape = box(i*32, 0, i*32+26, 18)
        inner = shape.buffer(-project.wall, join_style="mitre")
        if inner.is_empty or inner.buffer(-project.shelf_width).is_empty:
            raise ValueError("Zmniejsz grubość ścianki/półki do testu luzów 26 × 18 mm.")
        top = 9
        body = union([extrude(shape, 0, project.back), extrude(shape.difference(inner), project.back-.01, top+project.front),
                      extrude(inner.difference(inner.buffer(-project.shelf_width)), top-project.shelf_thickness, top)])
        parts.append(Part(f"T{i}-body", f"TOL_{clearance:.2f}_BODY", "body", body, project.body_color))
        parts.append(Part(f"T{i}-front", f"TOL_{clearance:.2f}_DIFFUSER", "diffuser", extrude(inner.buffer(-clearance), top, top+project.front), project.front_color))
    return parts


def tolerance_zip(project):
    if project.back+project.shelf_thickness >= 9:
        raise ValueError("Test luzów wymaga sumy grubości tyłu i półki mniejszej niż 9 mm.")
    parts = tolerance_parts(project)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("TOLERANCE_PRINT.3mf", three_mf(parts, "print", project.printer[0]))
        for p in parts:
            mesh = p.mesh.copy()
            mesh.apply_translation(-mesh.bounds[0])
            z.writestr(p.name+".stl", mesh.export(file_type="stl"))
        z.writestr("INSTRUKCJA.txt", "Cztery próbki luzu NA STRONĘ: 0,15 / 0,25 / 0,35 / 0,45 mm.\n"
                   "Rozpoznawaj próbki po nazwach części; modele nie mają oznaczeń wytłoczonych.\n"
                   "Drukuj korpus i front osobno, tymi samymi materiałami i ustawieniami co litery.\n"
                   "Front ma leżeć na półce, bez wciskania; podstawowe zamknięcie wymaga kleju.\n"
                   "Wybierz luz po schłodzeniu próbek; sprawdź skurcz i kompensację elephant foot.\n")
    return buf.getvalue()
