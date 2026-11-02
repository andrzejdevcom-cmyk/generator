from dataclasses import dataclass

import numpy as np
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity, make_valid
from shapely.geometry import GeometryCollection, LineString, Polygon
from shapely.ops import nearest_points, polygonize, unary_union

from backend.fonts import resolve_font
from backend.models import Project


def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g] if g.area > 1e-7 else []
    return [p for x in getattr(g, "geoms", []) for p in polygons(x)]


def clean(g):
    return unary_union(polygons(make_valid(g)))


class FlattenPen(BasePen):
    """Adaptive Bézier subdivision, controlled by error in millimetres."""
    def __init__(self, glyph_set, tolerance):
        super().__init__(glyph_set)
        self.tolerance = tolerance
        self.rings = []
        self.current = []

    def _moveTo(self, p):
        self.current = [p]

    def _lineTo(self, p):
        self.current.append(p)

    def flatten(self, points, level=0):
        a, b = np.array(points[0]), np.array(points[-1])
        v = b - a
        distance = max((np.linalg.norm(np.array(p) - a) if np.dot(v, v) < 1e-16 else
                        np.linalg.norm(np.array(p) - (a + np.clip(np.dot(np.array(p)-a, v)/np.dot(v, v), 0, 1)*v)))
                       for p in points[1:-1])
        if distance <= self.tolerance or level >= 14:
            self.current.append(tuple(b))
            return
        layers = [np.array(points, dtype=float)]
        while len(layers[-1]) > 1:
            layers.append((layers[-1][:-1] + layers[-1][1:]) / 2)
        self.flatten([l[0] for l in layers], level+1)
        self.flatten([l[-1] for l in reversed(layers)], level+1)

    def _curveToOne(self, a, b, c):
        self.flatten([self._getCurrentPoint(), a, b, c])

    def _qCurveToOne(self, a, b):
        self.flatten([self._getCurrentPoint(), a, b])

    def _closePath(self):
        if len(self.current) >= 3:
            self.rings.append(self.current + [self.current[0]])
        self.current = []

    def _endPath(self):
        self._closePath()


def outline(glyph_set, glyph_name, tolerance):
    pen = FlattenPen(glyph_set, tolerance)
    glyph_set[glyph_name].draw(pen)
    if not pen.rings:
        return GeometryCollection()
    # Non-zero winding preserves holes AND overlapping composite contours.
    def winding(x, y):
        n = 0
        for ring in pen.rings:
            for (ax, ay), (bx, by) in zip(ring, ring[1:]):
                cross = (bx-ax)*(y-ay) - (x-ax)*(by-ay)
                if ay <= y < by and cross > 0:
                    n += 1
                elif by <= y < ay and cross < 0:
                    n -= 1
        return n
    cells = polygonize(unary_union([LineString(r) for r in pen.rings]))
    return clean(unary_union([p for p in cells if winding(*p.representative_point().coords[0]) != 0]))


@dataclass
class GlyphShape:
    id: str
    label: str
    shape: object


def text_shapes(project: Project) -> list[GlyphShape]:
    path = resolve_font(project.font_id)
    data = path.read_bytes()
    tt = TTFont(path)
    glyph_set = tt.getGlyphSet()
    h = outline(glyph_set, "H" if "H" in glyph_set else tt.getGlyphOrder()[1], 1)
    cap_height = h.bounds[3] - h.bounds[1] if not h.is_empty else tt["head"].unitsPerEm * .72
    scale = project.height / cap_height
    hb_font = hb.Font(hb.Face(data))
    hb_font.scale = (tt["head"].unitsPerEm, tt["head"].unitsPerEm)
    hb.ot_font_set_funcs(hb_font)
    cmap = tt.getBestCmap()
    missing = sorted({c for c in project.text if not c.isspace() and ord(c) not in cmap})
    if missing:
        raise ValueError("Font nie zawiera znaków: " + " ".join(missing))
    shapes = []
    cache = {}
    for row, line in enumerate(project.text.split("\n")):
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {"kern": True})
        x, y = 0, -row * project.height * project.line_spacing
        for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
            name = tt.getGlyphName(info.codepoint)
            if name not in cache:
                cache[name] = outline(glyph_set, name, .04/scale)
            g = affinity.scale(cache[name], xfact=scale, yfact=scale, origin=(0, 0))
            g = affinity.translate(g, x + pos.x_offset*scale, y + pos.y_offset*scale)
            if not g.is_empty:
                if project.bridge_accents:
                    pieces = sorted(polygons(g), key=lambda p: p.area, reverse=True)
                    joined = pieces[0]
                    for piece in pieces[1:]:
                        a, b = nearest_points(joined, piece)
                        joined = unary_union([joined, piece, LineString([a, b]).buffer(project.bridge_width/2)])
                    g = joined
                shapes.append(GlyphShape(f"L{row+1}_{i+1}", line[info.cluster:info.cluster+1] or name, g))
            x += pos.x_advance*scale + project.spacing
            y += pos.y_advance*scale
    tt.close()
    if not shapes:
        raise ValueError("Tekst nie zawiera obrysów do wydrukowania.")
    bounds = unary_union([s.shape for s in shapes]).bounds
    width = bounds[2] - bounds[0]
    sx = project.width_scale / 100
    sy = 1
    if project.target_width:
        sx = project.target_width / width
        if project.proportional:
            sy = sx
    for s in shapes:
        s.shape = affinity.translate(s.shape, -bounds[0], -bounds[1])
        s.shape = affinity.scale(s.shape, sx, sy, origin=(0, 0))
        if project.corner_radius:
            rounded = s.shape.buffer(-project.corner_radius).buffer(project.corner_radius)
            if rounded.is_empty or rounded.area < s.shape.area*.8 or len(polygons(rounded)) != len(polygons(s.shape)):
                raise ValueError("Promień zaokrąglenia usuwa detale litery. Zmniejsz promień.")
            s.shape = clean(rounded)
    if project.joined:
        joined = shapes[0].shape
        for s in shapes[1:]:
            a, b = nearest_points(joined, s.shape)
            joined = unary_union([joined, s.shape, LineString([a, b]).buffer(project.bridge_width/2)])
        return [GlyphShape("WORD", "Napis", clean(joined))]
    return shapes
