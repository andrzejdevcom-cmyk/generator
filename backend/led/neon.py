import math

import numpy as np
from scipy.ndimage import convolve
from shapely import contains_xy
from shapely.geometry import LineString
from skimage.morphology import skeletonize

from backend.models import Issue, NeonPath


def centerlines(shape, cfg):
    """Raster medial skeleton, traced into paths split at branch vertices. No single-strip assumption."""
    x0, y0, x1, y1 = shape.bounds
    step = max(.6, max(x1-x0, y1-y0)/550)
    xs = np.arange(x0-step, x1+2*step, step)
    ys = np.arange(y0-step, y1+2*step, step)
    grid_x, grid_y = np.meshgrid(xs, ys)
    skeleton = skeletonize(contains_xy(shape, grid_x, grid_y))
    nodes = set(map(tuple, np.argwhere(skeleton)))
    graph = {}
    for r, c in nodes:
        neighbours = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            other = (r+dr, c+dc)
            if other not in nodes:
                continue
            if dr and dc and ((r+dr, c) in nodes or (r, c+dc) in nodes):
                continue
            neighbours.append(other)
        graph[(r, c)] = neighbours
    visited, paths = set(), []
    starts = sorted(nodes, key=lambda n: len(graph[n]) == 2)
    for start in starts:
        for following in graph[start]:
            edge = frozenset((start, following))
            if edge in visited:
                continue
            run = [start, following]
            visited.add(edge)
            prev, curr = start, following
            while len(graph[curr]) == 2:
                nxt = next(n for n in graph[curr] if n != prev)
                edge = frozenset((curr, nxt))
                if edge in visited:
                    break
                visited.add(edge)
                run.append(nxt)
                prev, curr = curr, nxt
            line = LineString([(xs[c], ys[r]) for r, c in run]).simplify(step*1.5)
            if line.length >= max(3, cfg.width):
                paths.append(NeonPath(id=f"neon-{len(paths)+1}", points=list(line.coords)))
    return paths, sum(len(n) > 2 for n in graph.values())


def bend_radii(points):
    """Circumcircle radius at every sampled bend; corners are not silently smoothed."""
    radii = []
    for a, b, c in zip(points, points[1:], points[2:]):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ab, bc, ac = np.linalg.norm(b-a), np.linalg.norm(c-b), np.linalg.norm(c-a)
        cross = abs(float((b-a)[0]*(c-a)[1]-(b-a)[1]*(c-a)[0]))
        if ab < 1e-6 or bc < 1e-6:
            radii.append(0)
        elif cross > 1e-7:
            # A polyline has sharp corners, irrespective of its circumcircle size.
            angle = math.acos(float(np.clip(np.dot(b-a, c-b)/(ab*bc), -1, 1)))
            radii.append(0 if angle > math.radians(12) else ab*bc*ac/(2*cross))
    return radii


def fillet_path(path, radius):
    """Replace planar corners with sampled, tangent circular fillets of the requested radius."""
    points = [np.array(p, dtype=float) for p in path.points]
    result = [tuple(points[0])]
    for a, b, c in zip(points, points[1:], points[2:]):
        u, v = a-b, c-b
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if min(lu, lv) < 1e-6:
            raise ValueError("Usuń powtórzone węzły ścieżki.")
        u, v = u/lu, v/lv
        theta = math.acos(float(np.clip(np.dot(u, v), -1, 1)))
        if abs(theta-math.pi) < .01:
            result.append(tuple(b))
            continue
        if theta < .02:
            raise ValueError("Nie można zaokrąglić zawrócenia o 180°.")
        tangent = radius/math.tan(theta/2)
        if tangent > min(lu, lv)*.48:
            raise ValueError("Za mało miejsca na zadany promień. Rozsuń węzły lub zmniejsz promień (zgodnie z profilem).")
        bisector = u+v
        center = b+bisector/np.linalg.norm(bisector)*radius/math.sin(theta/2)
        start, end = b+u*tangent, b+v*tangent
        a0 = math.atan2(*(start-center)[::-1])
        a1 = math.atan2(*(end-center)[::-1])
        delta = (a1-a0+math.pi)%(2*math.pi)-math.pi
        count = max(3, math.ceil(abs(delta)/math.radians(5)))
        result.extend(tuple(center+radius*np.array([math.cos(t), math.sin(t)]))
                      for t in np.linspace(a0, a0+delta, count+1))
    result.append(tuple(points[-1]))
    return NeonPath(id=path.id, points=result)


def check_paths(project, shape, paths):
    issues, occupied = [], []
    cfg = project.led
    if not paths:
        issues.append(Issue(severity="error", code="no_neon_paths", message="Brak tras Neon Flex. Wygeneruj linie środkowe lub narysuj ścieżkę."))
    if cfg.bend_direction == "top":
        issues.append(Issue(severity="error", code="bend_direction", message="Płaski rowek XY wymaga profilu z gięciem bocznym. Gięcie pionowe wymaga przestrzennej trasy, której ten generator nie tworzy."))
    if cfg.seat_depth > cfg.height:
        issues.append(Issue(severity="warning", code="buried_neon", message="Profil Neon Flex jest całkowicie schowany poniżej krawędzi rowka."))
    for p in paths:
        line = LineString(p.points)
        slot = line.buffer(cfg.width/2+cfg.clearance)
        if not shape.buffer(-project.wall).covers(slot):
            issues.append(Issue(severity="error", code="neon_outside", element_id=p.id,
                                message=f"Trasa {p.id}: rowek z luzem narusza obrys lub minimalną ściankę {project.wall:g} mm."))
        if not line.is_simple:
            issues.append(Issue(severity="error", code="neon_self_cross", element_id=p.id, message=f"Trasa {p.id} przecina samą siebie."))
        radii = bend_radii(p.points)
        if radii and min(radii) < cfg.min_radius-.05:
            issues.append(Issue(severity="error", code="neon_radius", element_id=p.id,
                                message=f"Trasa {p.id}: zbyt ostry zakręt (minimum {cfg.min_radius:g} mm). Użyj zaokrąglania i sprawdź obrys."))
        remainder = line.length % cfg.cut_length
        if min(remainder, cfg.cut_length-remainder) > .15:
            issues.append(Issue(severity="error", code="neon_cut", element_id=p.id,
                                message=f"Trasa {p.id}: {line.length:.2f} mm nie jest wielokrotnością cięcia {cfg.cut_length:g} mm (tolerancja 0,15 mm)."))
        for other, region in occupied:
            if region.intersection(slot).area > .05:
                issues.append(Issue(severity="error", code="neon_branch", element_id=p.id,
                                    message=f"Rowki {other} i {p.id} łączą się lub krzyżują. Rozdziel sekcje i zaplanuj przewody."))
        occupied.append((p.id, slot))
    return issues
