import math

import trimesh
from shapely.geometry import LineString

from backend.geometry.solids import Part, difference, disk, extrude, union
from backend.models import Issue


def segment_parts(project, parts, material, placements):
    """Grid cuts with separate two-pin back joiners; reject cuts without supported sockets."""
    if not project.segment:
        return parts, []
    issues, out = [], []
    max_size = min(project.segment_size, project.printer[0]-8, project.printer[1]-8)
    connectors = []
    # Only printable bodies need structural joins. Front segments are glued on their shelves.
    for part in parts:
        if not part.printable or part.kind not in ("body", "solid", "diffuser", "base"):
            out.append(part)
            continue
        x0, y0, z0 = part.mesh.bounds[0]
        x1, y1, z1 = part.mesh.bounds[1]
        nx, ny = math.ceil((x1-x0)/max_size), math.ceil((y1-y0)/max_size)
        if nx == ny == 1:
            out.append(part)
            continue
        if project.base:
            issues.append(Issue(severity="error", code="segment_rear_base", message="Podział zintegrowanej płyty tylnej nie jest obsługiwany. Wyłącz płytę przed segmentacją."))
            out.append(part)
            continue
        if part.kind == "base":
            issues.append(Issue(severity="error", code="segment_base", message="Podział wspólnej podstawy nie jest obsługiwany. Wyłącz podstawę lub dopasuj ją do stołu."))
            out.append(part)
            continue
        if part.kind in ("body", "solid"):
            depth = min(project.back-.6, 3) if part.kind == "body" else min(project.depth-1, 4)
            if depth < .8:
                issues.append(Issue(severity="error", code="segment_back", message="Tył jest za cienki na gniazda łączników. Zwiększ go do min. 1,4 mm."))
            cuts = []
            seams = [(0, x0+(x1-x0)*i/nx) for i in range(1, nx)] + [(1, y0+(y1-y0)*i/ny) for i in range(1, ny)]
            for seam_index, (axis, value) in enumerate(seams):
                # Keep every mounting feature away from the cut.
                blocked = any(abs((p.x if axis == 0 else p.y)-value) < max(p.length, p.width, p.diameter)/2+3 for p in placements)
                if blocked:
                    issues.append(Issue(severity="error", code="seam_feature", message="Linia podziału przecina obszar mocowania/LED. Zmień rozmiar segmentu lub położenie elementu."))
                    continue
                line = LineString([(value, y0), (value, y1)]) if axis == 0 else LineString([(x0, value), (x1, value)])
                cross = material.intersection(line)
                candidates = [cross] if cross.geom_type == "LineString" else list(getattr(cross, "geoms", []))
                placed = False
                for interval in sorted(candidates, key=lambda g: g.length, reverse=True):
                    if interval.length < project.pin_diameter+5:
                        continue
                    center = interval.interpolate(.5, normalized=True)
                    span = project.pin_diameter+2
                    a = (center.x-span, center.y) if axis == 0 else (center.x, center.y-span)
                    b = (center.x+span, center.y) if axis == 0 else (center.x, center.y+span)
                    r = project.pin_diameter/2
                    plate = LineString([a, b]).buffer(r+1.5)
                    if not material.covers(plate):
                        continue
                    # blind sockets open at the rear, leaving a solid roof
                    cuts.extend(extrude(disk(*p, r+project.clearance), -.1, depth) for p in (a, b))
                    joiner = union([extrude(plate, -2, 0), *[extrude(disk(*p, r), -.1, depth-project.clearance) for p in (a, b)]])
                    connectors.append(Part(f"{part.id}-join-{seam_index+1}", f"{part.name}_JOIN_{seam_index+1}", "joiner", joiner, project.body_color))
                    placed = True
                    break
                if not placed:
                    issues.append(Issue(severity="error", code="no_joiner", message=f"{part.name}: brak materiału na bezpieczne gniazda przy linii podziału. Zmień rozmiar segmentu/font."))
            part.mesh = difference(part.mesh, cuts)
        for ix in range(nx):
            for iy in range(ny):
                xa, xb = x0+(x1-x0)*ix/nx, x0+(x1-x0)*(ix+1)/nx
                ya, yb = y0+(y1-y0)*iy/ny, y0+(y1-y0)*(iy+1)/ny
                clip = trimesh.creation.box(extents=[xb-xa, yb-ya, z1-z0+2],
                                            transform=trimesh.transformations.translation_matrix([(xa+xb)/2, (ya+yb)/2, (z0+z1)/2]))
                mesh = trimesh.boolean.intersection([part.mesh, clip], engine="manifold")
                if mesh is not None and len(mesh.faces) and mesh.volume > .001:
                    out.append(Part(f"{part.id}-S{ix+1}-{iy+1}", f"{part.name}_S{ix+1}_{iy+1}", part.kind, mesh, part.color))
    if connectors:
        issues.append(Issue(severity="info", code="joiner_assembly", message="Łączniki dwukołkowe są osobnymi częściami od tyłu. Zwiększają grubość montażową o 2 mm; fronty dzielone należy wkleić. Sprawdź próbę tolerancji."))
    return out + connectors, issues
