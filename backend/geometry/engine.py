from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, box, mapping
from shapely.ops import unary_union

from backend.geometry.segmentation import segment_parts
from backend.geometry.solids import Part, difference, extrude, union
from backend.geometry.text import clean, polygons, text_shapes
from backend.led.layout import (check_placements, electrical, mounting_geometry,
                                placement_envelope, suggest_placements)
from backend.led.neon import centerlines, check_paths
from backend.models import Issue, Project
from backend.validation import validate_parts


@dataclass
class Generated:
    project: Project
    parts: list
    issues: list
    outlines: list
    cavity: object
    placements: list
    paths: list
    stats: dict

    @property
    def valid(self):
        return not any(i.severity == "error" for i in self.issues)

    def response(self, include_mesh=True):
        return {"project": self.project.model_dump(mode="json"), "valid": self.valid,
                "parts": [p.info(include_mesh) for p in self.parts],
                "issues": [i.model_dump() for i in self.issues], "outlines": self.outlines,
                "cavity": mapping(self.cavity), "placements": [p.model_dump() for p in self.placements],
                "neon_paths": [p.model_dump() for p in self.paths], "stats": self.stats}


def generate(project: Project):
    glyphs = text_shapes(project)
    material = clean(unary_union([g.shape for g in glyphs]))
    cavities = [clean(g.shape.buffer(-project.wall, join_style="round")) for g in glyphs]
    cavity = clean(unary_union(cavities))
    issues, parts, outlines = [], [], []
    rear_cuts = []
    if not project.joined:
        for i, g in enumerate(glyphs):
            for other in glyphs[i+1:]:
                if g.shape.intersection(other.shape).area > .01:
                    issues.append(Issue(severity="error", code="overlap_letters", message="Oddzielne litery nakładają się. Zwiększ odstęp lub włącz połączony napis."))
                    break
    placements = list(project.led.placements) if project.mode == "led" else []
    paths = list(project.led.neon_paths) if project.mode == "neon" else []
    if project.mode == "led":
        if project.led.auto:
            placements = [*suggest_placements(project, cavity), *placements]
            if not any(p.kind in ("strip", "pcb") for p in placements):
                issues.append(Issue(severity="error", code="auto_no_fit", message="Nie znaleziono miejsca na wybrany LED z mocowaniami. Zwiększ literę lub zmniejsz profil LED."))
        issues.extend(check_placements(project, cavity, material, placements))
    if project.mode == "neon":
        if not paths and project.led.auto:
            paths, branches = centerlines(material, project.led)
            if branches:
                issues.append(Issue(severity="warning", code="skeleton_branches", message=f"Szkielet zawiera {branches} węzłów rozgałęzień; trasy są osobnymi sekcjami. Popraw końce i promienie w edytorze."))
        issues.extend(check_paths(project, material, paths))
    invalid_ids = {i.element_id for i in issues if i.severity == "error" and i.element_id}
    for glyph, inner in zip(glyphs, cavities):
        g = glyph.shape
        outlines.append({"id": glyph.id, "label": glyph.label, "geometry": mapping(g)})
        if project.mode == "solid":
            parts.append(Part(glyph.id+"-body", f"{glyph.id}_{glyph.label}_SOLID", "solid", extrude(g, 0, project.depth), project.body_color))
            continue
        if project.mode == "neon":
            slots = unary_union([LineString(p.points).buffer(project.led.width/2+project.led.clearance) for p in paths if p.id not in invalid_ids])
            body = union([extrude(g, 0, project.depth-project.led.seat_depth),
                          extrude(g.difference(slots), project.depth-project.led.seat_depth, project.depth)])
            parts.append(Part(glyph.id+"-body", f"{glyph.id}_{glyph.label}_NEON", "body", body, project.body_color))
            continue
        if inner.is_empty:
            issues.append(Issue(severity="error", code="empty_cavity", element_id=glyph.id,
                                message=f"Litera {glyph.label} nie ma komory przy ściance {project.wall:g} mm. Zwiększ wysokość lub zmniejsz ściankę."))
            continue
        for island in polygons(g):
            if island.buffer(-project.wall-project.clearance).is_empty:
                issues.append(Issue(severity="error", code="detail_no_cavity", element_id=glyph.id,
                                    message=f"Litera {glyph.label}: oddzielny detal nie mieści komory i frontu. Zwiększ wysokość lub zmień font/ściankę; detal nie został usunięty."))
        # A morphological opening detects strokes that disappear in inward offsets.
        lost = g.difference(inner.buffer(project.wall+.05)).area
        if lost > max(1, g.area*.025):
            issues.append(Issue(severity="warning", code="offset_detail", element_id=glyph.id,
                                message=f"Litera {glyph.label}: wąskie detale nie mieszczą pełnej komory. Obrys pozostaje zachowany; sprawdź przekrój."))
        shelf_top = project.depth-project.front
        shelf_open = clean(inner.buffer(-project.shelf_width))
        shelf = clean(inner.difference(shelf_open))
        wall = clean(g.difference(inner))
        body = union([extrude(g, 0, project.back), extrude(wall, project.back-.01, project.depth),
                      extrude(shelf, shelf_top-project.shelf_thickness, shelf_top)])
        adds, cuts = [], []
        for p in placements:
            if p.id in invalid_ids or not g.covers(placement_envelope(p, 0)):
                continue
            a, c, refs = mounting_geometry(project, p)
            adds.extend(a)
            cuts.extend(c)
            rear_cuts.extend(c)
            for n, ref in enumerate(refs):
                parts.append(Part(f"{p.id}-ref-{n}", f"REF_{p.id}", "electronics", ref, "#ffa94d", False))
        body = difference(union([body, *adds]), cuts)
        diffuser_shape = clean(inner.buffer(-project.clearance))
        if diffuser_shape.is_empty:
            issues.append(Issue(severity="error", code="empty_front", element_id=glyph.id, message="Luz usuwa cały dyfuzor. Zmniejsz luz lub zwiększ literę."))
        else:
            front = extrude(diffuser_shape, shelf_top, project.depth)
            if project.collar:
                collar_outer = clean(shelf_open.buffer(-project.clearance))
                collar = clean(collar_outer.difference(collar_outer.buffer(-.8)))
                if collar.is_empty:
                    issues.append(Issue(severity="error", code="collar_no_fit", message="Brak miejsca na kołnierz pozycjonujący."))
                else:
                    front = union([front, extrude(collar, shelf_top-min(1, project.shelf_thickness), shelf_top+.01)])
            parts.append(Part(glyph.id+"-diffuser", f"{glyph.id}_{glyph.label}_DIFFUSER", "diffuser", front, project.front_color))
        parts.append(Part(glyph.id+"-body", f"{glyph.id}_{glyph.label}_BODY", "body", body, project.body_color))
    if project.mode == "neon":
        for p in paths:
            if p.id in invalid_ids:
                continue
            ref = extrude(LineString(p.points).buffer(project.led.width/2),
                          project.depth-project.led.seat_depth, project.depth-project.led.seat_depth+project.led.height)
            parts.append(Part(p.id+"-ref", "REF_"+p.id, "electronics", ref, "#ffb454", False))
    if project.base:
        # Rear plinth crosses the full footprint, supporting every row and detached accent.
        x0, y0, x1, y1 = material.bounds
        base = extrude(box(x0-project.base_depth/2, y0-project.base_depth/2,
                           x1+project.base_depth/2, y1+project.base_depth/2), -project.base_thickness, 0)
        bodies = [p for p in parts if p.kind in ("body", "solid")]
        if bodies:
            combined = difference(union([base, *[p.mesh for p in bodies]]), rear_cuts)
            parts = [p for p in parts if p not in bodies]
            parts.append(Part("BASE_BODY", "WORD_BASE_BODY", "body", combined, project.body_color))
    parts, split_issues = segment_parts(project, parts, material, placements)
    issues.extend(split_issues)
    issues.extend(validate_parts(project, parts))
    printable = [p for p in parts if p.printable]
    volume = sum(max(0, p.mesh.volume) for p in printable)
    mass = volume/1000*project.material_density
    all_bounds = np.array([p.mesh.bounds for p in parts]) if parts else np.zeros((1, 2, 3))
    bounds = np.array([all_bounds[:, 0, :].min(axis=0), all_bounds[:, 1, :].max(axis=0)])
    stats = {"bounds": bounds.tolist(), "dimensions": (bounds[1]-bounds[0]).tolist(),
             "volume_mm3": round(volume, 2), "mass_g": round(mass, 2),
             "cost_pln": round(mass/1000*project.price_per_kg, 2),
             "mass_note": "Objętość brył × gęstość. Pełny materiał, bez ustawień wypełnienia i strat slicera.",
             "printable_parts": len(printable), "electrical": electrical(project, placements, paths)}
    return Generated(project, parts, issues, outlines, cavity, placements, paths, stats)
