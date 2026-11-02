import math

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from backend.geometry.solids import difference, disk, extrude, footprint, place_shape
from backend.geometry.text import polygons
from backend.models import Issue, Placement, Project


def placement_envelope(p, clearance):
    if p.kind in ("wire", "screw", "magnet", "standoff"):
        r = p.diameter/2 + (2 if p.kind == "standoff" else 0)
        return disk(p.x, p.y, r + clearance)
    if p.kind == "keyhole":
        local = unary_union([disk(0, 0, p.diameter/2), box(-p.diameter/4, 0, p.diameter/4, p.diameter*1.5)])
        return place_shape(local, p).buffer(clearance)
    margin = (1.4 if p.fixing != "adhesive" else 0) if p.kind in ("strip", "pcb") else 0
    return footprint(p, margin + clearance)


def suggest_placements(project: Project, cavity):
    """Conservative rectangle packing; each proposal passes the same envelope test as manual edits."""
    cfg = project.led
    kind = "pcb" if cfg.source == "pcb" else "strip"
    length = cfg.pcb_length if kind == "pcb" else max(12, min(40, project.height*.28))
    found = []
    for island in polygons(cavity):
        region = island
        for _ in range(3):
            if region.is_empty:
                break
            x0, y0, x1, y1 = region.bounds
            candidates = [region.representative_point()]
            step = max(2, min(cfg.width/2, (x1-x0)/12, (y1-y0)/12))
            candidates.extend(Point(x, y) for x in np.arange(x0+step/2, x1, step)
                              for y in np.arange(y0+step/2, y1, step) if region.contains(Point(x, y)))
            candidates.sort(key=lambda p: p.distance(region.boundary), reverse=True)
            best = None
            for point in candidates[:350]:
                for angle in (0, 90, 60, 120, 45, 135, 30, 150, 15, 165, 75, 105):
                    p = Placement(id=f"auto-{len(found)+1}", kind=kind, x=point.x, y=point.y,
                                  angle=angle, width=cfg.width, length=length, height=cfg.height,
                                  fixing=cfg.fixing, mounting_points=cfg.mounting_points, wire_exit=cfg.wire_exit)
                    env = placement_envelope(p, cfg.clearance)
                    if region.covers(env):
                        best = p
                        break
                if best:
                    break
            if best is None:
                break
            found.append(best)
            region = region.difference(placement_envelope(best, cfg.clearance).buffer(3))
    return found


def check_placements(project, cavity, material, placements):
    issues = []
    occupied = []
    for p in placements:
        env = placement_envelope(p, project.led.clearance)
        allowed = cavity if p.kind in ("strip", "pcb", "standoff", "connector") else material
        if not allowed.covers(env):
            point = Point(p.x, p.y)
            # Local inscribed diameter, conservative for arbitrary orientation.
            available = max(0, 2 * point.distance(allowed.boundary)) if allowed.contains(point) else 0
            issues.append(Issue(severity="error", code="placement_outside",
                                element_id=p.id, message=f"Element {p.id}: wybrana szerokość {p.width:g} mm; "
                                f"lokalna średnica wpisana {available:.1f} mm. Obrys z luzem/mocowaniami nie mieści się. "
                                "Przesuń element, zwiększ literę, zmień font albo wybierz węższy profil."))
        if p.kind in ("strip", "pcb", "standoff", "connector"):
            top = project.back + p.height + (2 if p.kind == "pcb" and p.fixing != "adhesive" else 0)
            if top >= project.depth-project.front-project.shelf_thickness:
                issues.append(Issue(severity="error", code="front_collision", element_id=p.id,
                                    message=f"Element {p.id} koliduje z poziomem półki/frontu. Zwiększ głębokość."))
        if p.kind == "pcb" and p.fixing != "adhesive" and (p.width < 6 or p.length < 8):
            issues.append(Issue(severity="error", code="pcb_mount_size", element_id=p.id,
                                message="Podstawki z otworami wymagają PCB co najmniej 8 × 6 mm. Dla mniejszych modułów użyj klejenia."))
        if p.kind == "pcb" and p.fixing != "adhesive":
            rows = math.ceil(p.mounting_points/2)
            if rows > 1 and (p.width-4)/(rows-1) < 2.8:
                issues.append(Issue(severity="error", code="pcb_mount_spacing", element_id=p.id,
                                    message="Otwory podstawek PCB leżą zbyt blisko siebie. Zmniejsz liczbę punktów lub zwiększ szerokość PCB."))
        if p.kind in ("strip", "pcb", "standoff", "connector"):
            for other, other_env in occupied:
                if env.intersection(other_env).area > .01:
                    issues.append(Issue(severity="error", code="component_collision", element_id=p.id,
                                        message=f"Elementy {other.id} i {p.id} kolidują."))
            occupied.append((p, env))
        if p.kind == "cable" and p.height >= project.back-.6:
            issues.append(Issue(severity="error", code="cable_depth", element_id=p.id,
                                message="Kanał przewodów musi pozostawić co najmniej 0,6 mm dna."))
        if p.kind == "magnet" and p.height >= project.back-.6:
            issues.append(Issue(severity="error", code="magnet_depth", element_id=p.id,
                                message="Kieszeń magnesu musi pozostawić co najmniej 0,6 mm dna. Zwiększ grubość tyłu."))
    return issues


def mounting_geometry(project, p):
    """Return additions to body, subtractions, and purchased-component reference solids."""
    z = project.back
    bottom = -project.base_thickness-.1 if project.base else -.1
    additions, cutters, refs = [], [], []
    if p.kind in ("strip", "pcb"):
        lift = 2 if p.kind == "pcb" and p.fixing != "adhesive" else 0
        refs.append(extrude(footprint(p), z+lift, z+lift+p.height))
        if p.fixing != "adhesive":
            if p.kind == "strip":
                for side in (-1, 1):
                    yy = side*(p.width/2+project.led.clearance+.5)
                    intervals = [(-p.length/2-1, p.length/2+1)] if p.fixing == "guides" else [(x-2, x+2) for x in (-max(0,p.length/2-2),0,max(0,p.length/2-2))]
                    for left, right in intervals:
                        rail = place_shape(box(left, yy-.5, right, yy+.5), p)
                        additions.append(extrude(rail, z-.1, z+min(p.height+.8, 5)))
            else:
                for i in range(p.mounting_points):
                    xx = (-1 if i%2 == 0 else 1)*(p.length/2-2)
                    rows = math.ceil(p.mounting_points/2)
                    yy = 0 if rows == 1 else (i//2/(rows-1)-.5)*max(0, p.width-4)
                    pad = place_shape(disk(xx, yy, 2), p)
                    hole = place_shape(disk(xx, yy, .9), p)
                    additions.append(extrude(pad, z-.1, z+2))
                    cutters.append(extrude(hole, z-.1, z+2.1))
                # Purchased PCB reference has the same mounting bores as its pads.
                board_holes = []
                for c in cutters:
                    cx, cy = c.bounds.mean(axis=0)[:2]
                    board_holes.append(extrude(disk(cx, cy, .9), z+1.9, z+2+p.height+.1))
                refs[0] = difference(refs[0], board_holes)
                if p.fixing == "holders":
                    for side in (-1, 1):
                        xx = side*(p.length/2+project.led.clearance+.5)
                        additions.append(extrude(place_shape(box(xx-.5,-p.width/2,xx+.5,p.width/2),p),z-.1,z+2.8))
    elif p.kind in ("wire", "screw"):
        cutters.append(extrude(disk(p.x, p.y, p.diameter/2), bottom, z+.1))
    elif p.kind == "keyhole":
        cut = unary_union([disk(0, 0, p.diameter/2), box(-p.diameter/4, 0, p.diameter/4, p.diameter*1.5)])
        cutters.append(extrude(place_shape(cut, p), bottom, z+.1))
    elif p.kind == "magnet":
        cutters.append(extrude(disk(p.x, p.y, p.diameter/2), z-p.height, z+.1))
    elif p.kind == "standoff":
        additions.append(extrude(disk(p.x, p.y, p.diameter/2+2), z-.1, z+p.height))
        cutters.append(extrude(disk(p.x, p.y, p.diameter/2), bottom, z+p.height+.1))
    elif p.kind == "cable":
        cutters.append(extrude(footprint(p), z-p.height, z+.1))
    elif p.kind == "connector":
        # A recessed connector seat with two actual retaining walls.
        refs.append(extrude(footprint(p), z, z+p.height))
        for side in (-1, 1):
            yy = side*(p.width/2+project.led.clearance+.5)
            additions.append(extrude(place_shape(box(-p.length/2, yy-.5, p.length/2, yy+.5), p),
                                      z-.1, z+p.height/2))
    return additions, cutters, refs


def electrical(project, placements, paths):
    runs = [p.length for p in placements if p.kind in ("strip", "pcb")]
    runs.extend(LineString(p.points).length for p in paths)
    length = sum(runs)
    pcbs = [p for p in placements if p.kind == "pcb"]
    centers = [(p.x, p.y) for p in placements if p.kind in ("strip", "pcb")]
    wire = sum(math.dist(a, b) for a, b in zip(centers, centers[1:]))*1.2
    return {"length_mm": round(length, 2), "sections_mm": [round(v, 2) for v in runs],
            "pcb_count": len(pcbs), "pcb_lengths_mm": [p.length for p in pcbs],
            "power_w": round(length/1000*project.led.watts_per_m, 2), "voltage": project.led.voltage,
            "wire_mm": round(wire, 1),
            "note": "Moc wg W/m (także dla PCB: wpisz wartość równoważną). Przewody: łańcuch między środkami +20%, bez dojścia do zasilacza. "
                    "Nie jest to dobór zasilacza ani analiza cieplna."}
