from dataclasses import dataclass

import numpy as np
import manifold3d
import trimesh
from shapely import affinity
from shapely.geometry import Point, box

from backend.geometry.text import polygons


def extrude(shape, z0, z1):
    if z1 <= z0 or shape.is_empty:
        return None
    contours = []
    for p in polygons(shape):
        contours.extend([np.array(p.exterior.coords)[:-1], *[np.array(r.coords)[:-1] for r in p.interiors]])
    if not contours:
        return None
    # Manifold's cross-section triangulation handles tangent/collinear offset
    # vertices that produced non-manifold vertical edges with extrude_polygon.
    solid = manifold3d.CrossSection(contours, manifold3d.FillRule.EvenOdd).extrude(z1-z0)
    output = solid.to_mesh64()
    mesh = trimesh.Trimesh(vertices=np.asarray(output.vert_properties)[:, :3], faces=np.asarray(output.tri_verts), process=True)
    mesh.apply_translation([0, 0, z0])
    if not mesh.is_volume:
        raise ValueError("Nie udało się wyciągnąć zamkniętej bryły z obrysu.")
    return mesh


def union(meshes):
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    if not meshes:
        return None
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold", check_volume=True)


def difference(mesh, cutters):
    cutters = [m for m in cutters if m is not None and len(m.faces)]
    if not cutters:
        return mesh
    return trimesh.boolean.difference([mesh, *cutters], engine="manifold", check_volume=True)


def footprint(p, margin=0):
    shape = box(-p.length/2-margin, -p.width/2-margin, p.length/2+margin, p.width/2+margin)
    return place_shape(shape, p)


def place_shape(shape, p):
    return affinity.translate(affinity.rotate(shape, p.angle, origin=(0, 0)), p.x, p.y)


def disk(x, y, radius):
    return Point(x, y).buffer(radius, quad_segs=24)


@dataclass
class Part:
    id: str
    name: str
    kind: str
    mesh: trimesh.Trimesh
    color: str
    printable: bool = True

    def info(self, include_mesh=True):
        result = {
            "id": self.id, "name": self.name, "kind": self.kind, "color": self.color,
            "printable": self.printable,
            "bounds": np.round(self.mesh.bounds, 5).tolist(),
            "volume_mm3": float(self.mesh.volume),
            "watertight": bool(self.mesh.is_watertight),
            "triangles": len(self.mesh.faces),
        }
        if include_mesh:
            result.update(vertices=np.round(self.mesh.vertices, 5).tolist(), faces=self.mesh.faces.tolist())
        return result
