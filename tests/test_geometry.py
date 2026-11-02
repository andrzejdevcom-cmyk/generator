import io
import json
import math
import zipfile

import lib3mf
import numpy as np
import pytest
import trimesh
from shapely.geometry import LineString, Point

from backend.export.files import project_zip, read_3mf, stl_bytes, three_mf
from backend.fonts import BUNDLED, import_font, resolve_font
from backend.geometry.engine import generate
from backend.geometry.solids import footprint
from backend.geometry.text import polygons, text_shapes
from backend.geometry.tolerance import tolerance_parts, tolerance_zip
from backend.led.layout import mounting_geometry, suggest_placements
from backend.led.neon import bend_radii, centerlines, check_paths, fillet_path
from backend.models import NeonPath, Placement, Project


def part(result, kind):
    return next(p for p in result.parts if p.kind == kind)


def all_sound(result):
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]
    for p in result.parts:
        assert p.mesh.is_watertight
        assert p.mesh.is_volume
        assert p.mesh.is_winding_consistent
        assert p.mesh.volume > 0


@pytest.mark.parametrize("letter,holes", [("A", 1), ("B", 2), ("O", 1)])
def test_01_02_03_counters_survive_in_outline_and_solid(letter, holes):
    project = Project(text=letter, mode="solid")
    shape = text_shapes(project)[0].shape
    assert sum(len(p.interiors) for p in polygons(shape)) == holes
    result = generate(project)
    all_sound(result)
    mesh = result.parts[0].mesh
    assert mesh.volume == pytest.approx(shape.area*project.depth, rel=2e-6)
    for polygon in polygons(shape):
        for hole in polygon.interiors:
            from shapely.geometry import Polygon
            point = Polygon(hole).representative_point()
            assert not mesh.contains([[point.x, point.y, project.depth/2]])[0]


def test_04_L_stroke_is_present_and_differs_from_L():
    crossed = text_shapes(Project(text="Ł", mode="solid"))[0].shape
    plain = text_shapes(Project(text="L", mode="solid"))[0].shape
    assert crossed.symmetric_difference(plain).area > 200
    all_sound(generate(Project(text="Ł", mode="solid")))


def test_05_polish_accents_are_preserved():
    result = generate(Project(text="ŻÓŁW", mode="solid"))
    all_sound(result)
    assert len(result.parts) == 4
    shapes = text_shapes(Project(text="ŻÓŁW", mode="solid"))
    assert len(polygons(shapes[0].shape)) == 2
    assert len(polygons(shapes[1].shape)) == 2
    assert any(i.code == "detached" for i in result.issues)


def test_06_text_scaling_spacing_and_harfbuzz_kerning():
    project = Project(text="3DAS", mode="solid", spacing=3)
    result = generate(project)
    all_sound(result)
    assert len(result.parts) == 4
    assert max(p.mesh.extents[1] for p in result.parts) == pytest.approx(120, abs=5)
    scaled = generate(project.model_copy(update={"target_width": 300}))
    assert scaled.stats["dimensions"][0] == pytest.approx(300, abs=.001)
    tighter = text_shapes(Project(text="AV", mode="solid", spacing=0))
    # Actual HarfBuzz shaping reduces the advance compared with an unkerned pair.
    from backend.fonts import resolve_font
    from fontTools.ttLib import TTFont
    import uharfbuzz as hb
    path = resolve_font(project.font_id)
    face = hb.Face(path.read_bytes())
    font = hb.Font(face)
    buf = hb.Buffer(); buf.add_str("AV"); buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True}); kerned = sum(p.x_advance for p in buf.glyph_positions)
    hb.shape(font, (buf2 := _buffer("AV")), {"kern": False}); unkerned = sum(p.x_advance for p in buf2.glyph_positions)
    assert kerned < unkerned
    spaced = text_shapes(Project(text="AV", mode="solid", spacing=8))
    assert spaced[1].shape.bounds[0]-tighter[1].shape.bounds[0] == pytest.approx(8)


def _buffer(text):
    import uharfbuzz as hb
    b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); return b


def test_07_hollow_A_has_real_back_walls_and_led_room():
    p = Project(led={"auto": True})
    result = generate(p)
    all_sound(result)
    body = part(result, "body").mesh
    cavity = result.cavity
    q = cavity.representative_point()
    assert body.contains([[q.x, q.y, 1]])[0]
    assert not body.contains([[q.x, q.y, 15]])[0]
    shape = text_shapes(p)[0].shape
    assert body.volume < shape.area*p.depth*.5
    assert result.placements
    assert all(cavity.covers(footprint(c, 1.7)) for c in result.placements)
    assert any(p.kind == "electronics" for p in result.parts)


def test_08_too_wide_led_is_blocked():
    result = generate(Project(led={"placements": [{"id": "too-wide", "x": 30, "y": 30, "width": 80, "length": 25}]}))
    assert not result.valid
    issues = [i for i in result.issues if i.code == "placement_outside"]
    assert issues and "80 mm" in issues[0].message


def test_09_wall_parameter_changes_actual_volume():
    r2 = generate(Project(wall=2))
    r3 = generate(Project(wall=3))
    all_sound(r2); all_sound(r3)
    assert part(r3, "body").mesh.volume > part(r2, "body").mesh.volume*1.15
    assert part(r3, "diffuser").mesh.volume < part(r2, "diffuser").mesh.volume
    assert r3.cavity.area < r2.cavity.area


def test_10_STL_and_3MF_round_trip_and_independent_lib3mf_validation():
    result = generate(Project())
    original = [p for p in result.parts if p.printable]
    data = three_mf(original)
    reread = read_3mf(data)
    assert len(reread) == len(original)
    for before, after in zip(original, reread):
        assert after.is_volume
        np.testing.assert_allclose(before.mesh.bounds, after.bounds, atol=1e-5)
        assert before.mesh.volume == pytest.approx(after.volume, rel=1e-6)
    scene = trimesh.load(io.BytesIO(data), file_type="3mf")
    assert len(scene.geometry) == 2
    np.testing.assert_allclose(scene.bounds, result.stats["bounds"], atol=1e-5)
    wrapper = lib3mf.get_wrapper(); model = wrapper.CreateModel(); reader = model.QueryReader("3mf")
    reader.SetStrictModeActive(True); reader.ReadFromBuffer(data)
    assert reader.GetWarningCount() == 0
    objects = model.GetMeshObjects(); count = 0
    while objects.MoveNext():
        assert objects.GetCurrentMeshObject().IsManifoldAndOriented()
        count += 1
    assert count == 2
    for before in original:
        stl = stl_bytes([before])
        mesh = trimesh.load(io.BytesIO(stl), file_type="stl")
        assert mesh.is_volume
        np.testing.assert_allclose(mesh.extents, before.mesh.extents, atol=2e-5)
        assert mesh.volume == pytest.approx(before.mesh.volume, rel=1e-5)


def test_11_project_json_round_trip_has_identical_parameters_and_geometry():
    p = Project(text="ŻÓŁW\n3DAS", led={"width": 8, "voltage": 24}, width_scale=85, spacing=3.5)
    restored = Project.model_validate_json(p.model_dump_json())
    assert p == restored
    a, b = generate(p), generate(restored)
    for m1, m2 in zip(a.parts, b.parts):
        np.testing.assert_allclose(m1.mesh.vertices, m2.mesh.vertices)
        np.testing.assert_array_equal(m1.mesh.faces, m2.mesh.faces)


def test_12_A1_mini_size_warning_and_actual_segmentation_with_joiners():
    large = generate(Project(text="I", height=260))
    assert any(i.code == "bed_size" for i in large.issues)
    split = generate(Project(text="I", height=260, segment=True, segment_size=130))
    all_sound(split)
    assert any(p.kind == "joiner" for p in split.parts)
    assert not any(i.code == "bed_size" for i in split.issues)
    assert sum(p.kind == "body" for p in split.parts) == 2
    # Joined pins occupy the blind sockets without intersecting the split bodies.
    joiner = part(split, "joiner").mesh
    for body in [p.mesh for p in split.parts if p.kind == "body"]:
        collision = trimesh.boolean.intersection([body, joiner], engine="manifold")
        assert collision.volume < .001


def test_13_front_rests_on_shelf_with_correct_clearance_and_no_collision():
    p = Project()
    r = generate(p)
    body, front = part(r, "body").mesh, part(r, "diffuser").mesh
    intersection = trimesh.boolean.intersection([body, front], engine="manifold")
    assert abs(intersection.volume) < .0001
    inner = r.cavity
    diffuser = inner.buffer(-p.clearance)
    assert diffuser.boundary.distance(inner.boundary) == pytest.approx(.25, abs=.01)
    shelf = inner.difference(inner.buffer(-p.shelf_width))
    supported = shelf.intersection(diffuser)
    assert supported.area > 10
    q = supported.representative_point()
    assert body.contains([[q.x, q.y, p.depth-p.front-.2]])[0]
    assert front.contains([[q.x, q.y, p.depth-p.front+.2]])[0]
    assert front.bounds[0, 2] == pytest.approx(23.8)


def test_14_rigid_PCB_dimensions_and_real_mounting_pads():
    base = Project(text="I", led={"source": "pcb"})
    shape = text_shapes(base)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    led = Placement(id="PCB", kind="pcb", x=cx, y=60, length=30, width=10, height=3, angle=90, mounting_points=4)
    p = base.model_copy(update={"led": base.led.model_copy(update={"placements": [led]})})
    r = generate(p); all_sound(r)
    ref = part(r, "electronics").mesh
    np.testing.assert_allclose(ref.extents, [10, 30, 3], atol=1e-6)
    np.testing.assert_allclose(ref.bounds[0, 2], p.back+2)
    adds, cuts, _ = mounting_geometry(p, led)
    assert len(adds) == len(cuts) == 4
    body = part(r, "body").mesh
    # Each pad's cylindrical bore remains open; its surrounding ring is solid.
    for a, c in zip(adds, cuts):
        center = c.bounds.mean(axis=0)
        assert not body.contains([[center[0], center[1], p.back+1]])[0]
        assert body.contains([[center[0]+1.5, center[1], p.back+1]])[0]


def test_15_neon_rejects_sharp_bends_and_wrong_cut_lengths_but_builds_valid_channel():
    p = Project(text="I", mode="neon", led={"source": "neon", "width": 6, "height": 8, "cut_length": 20})
    shape = text_shapes(p)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    valid_path = NeonPath(id="N", points=[(cx, 20), (cx, 100)])
    valid = p.model_copy(update={"led": p.led.model_copy(update={"neon_paths": [valid_path]})})
    r = generate(valid); all_sound(r)
    body = part(r, "body").mesh
    assert not body.contains([[cx, 60, 23]])[0]
    assert body.contains([[cx, 60, 19]])[0]
    invalid = [NeonPath(id="sharp", points=[(cx, 20), (cx, 60), (cx+5, 60)]),
               NeonPath(id="cut", points=[(cx, 20), (cx, 103)])]
    issues = check_paths(p, shape, invalid)
    assert any(i.code == "neon_radius" for i in issues)
    assert any(i.code == "neon_cut" for i in issues)
    curved = fillet_path(NeonPath(id="f", points=[(0, 0), (50, 0), (50, 50)]), 15)
    assert min(bend_radii(curved.points)) == pytest.approx(15, abs=.02)


def test_real_wire_screw_keyhole_magnet_and_cable_cuts():
    p = Project(text="I", back=4)
    g = text_shapes(p)[0].shape
    cx = (g.bounds[0]+g.bounds[2])/2
    ps = [Placement(id="wire", kind="wire", x=cx, y=20, diameter=5),
          Placement(id="key", kind="keyhole", x=cx, y=40, diameter=5),
          Placement(id="mag", kind="magnet", x=cx, y=70, diameter=6, height=2),
          Placement(id="cable", kind="cable", x=cx, y=95, width=3, length=8, height=1)]
    r = generate(p.model_copy(update={"led": p.led.model_copy(update={"placements": ps})})); all_sound(r)
    mesh = part(r, "body").mesh
    assert not mesh.contains([[cx, 20, 1], [cx, 40, 1], [cx, 70, 3], [cx, 95, 3.5]]).any()
    assert mesh.contains([[cx, 70, 1], [cx, 95, 1]]).all()


def test_collar_is_supported_without_colliding():
    r = generate(Project(collar=True)); all_sound(r)
    front, body = part(r, "diffuser").mesh, part(r, "body").mesh
    assert front.bounds[0, 2] == pytest.approx(22.8, abs=.001)
    assert trimesh.boolean.intersection([front, body], engine="manifold").volume < .001


def test_wire_hole_passes_through_integrated_rear_base():
    p = Project(text="I", base=True)
    shape = text_shapes(p)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    p.led.placements = [Placement(id="wire", kind="wire", x=cx, y=60)]
    r = generate(p); all_sound(r)
    mesh = part(r, "body").mesh
    assert not mesh.contains([[cx, 60, -1], [cx, 60, 1]]).any()


def test_holders_change_printed_geometry_relative_to_continuous_guides():
    p = Project(text="I")
    shape = text_shapes(p)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    placement = Placement(id="led", x=cx, y=60, angle=90, length=35, fixing="guides")
    p.led.placements = [placement]
    guides = generate(p); all_sound(guides)
    p.led.placements = [placement.model_copy(update={"fixing": "holders"})]
    holders = generate(p); all_sound(holders)
    assert part(guides, "body").mesh.volume > part(holders, "body").mesh.volume


def test_pcb_adhesive_mount_is_on_back_and_dense_mounting_holes_are_blocked():
    p = Project(text="I")
    shape = text_shapes(p)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    item = Placement(id="pcb", kind="pcb", x=cx, y=60, angle=90, fixing="adhesive")
    p.led.placements = [item]
    result = generate(p); all_sound(result)
    assert part(result, "electronics").mesh.bounds[0, 2] == pytest.approx(p.back)
    p.led.placements = [item.model_copy(update={"fixing": "holders", "mounting_points": 12})]
    result = generate(p)
    assert not result.valid and any(i.code == "pcb_mount_spacing" for i in result.issues)


def test_duplicate_ids_are_rejected_and_small_accents_are_not_silently_lost():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="unikalne"):
        Project(led={"placements": [{"id": "same"}, {"id": "same"}]})
    r = generate(Project(text="i", height=20, wall=2))
    assert not r.valid
    assert any(i.code in ("detail_no_cavity", "empty_cavity") for i in r.issues)


def test_bridge_detached_accents_joined_words_and_rear_base():
    p = Project(text="Ż", mode="solid", bridge_accents=True)
    r = generate(p); all_sound(r)
    assert len(part(r, "solid").mesh.split()) == 1
    joined = generate(Project(text="AB", mode="solid", joined=True)); all_sound(joined)
    assert len(joined.parts) == 1 and len(joined.parts[0].mesh.split()) == 1
    based = generate(Project(text="AB", base=True)); all_sound(based)
    assert sum(p.kind == "body" for p in based.parts) == 1
    assert based.stats["bounds"][0][2] == -3


def test_font_identity_import_missing_characters_and_missing_font(tmp_path, monkeypatch):
    import backend.fonts as fonts
    monkeypatch.setattr(fonts, "USER_FONTS", tmp_path)
    data = BUNDLED["dejavu-sans"][1].read_bytes()
    font = import_font(data)
    assert font["id"].startswith("user-") and len(font["id"]) == 69
    assert resolve_font(font["id"]).read_bytes() == data
    all_sound(generate(Project(text="ąćęłńóśźż ĄĆĘŁŃÓŚŹŻ", mode="solid", font_id=font["id"])))
    with pytest.raises(ValueError, match="Brakuje fontu"):
        generate(Project(font_id="user-"+"0"*64))
    with pytest.raises(ValueError, match="nie zawiera"):
        generate(Project(text="\U0001fae0"))
    with pytest.raises(ValueError):
        import_font(b"NOTAFONT")
    with pytest.raises(ValueError, match="10 MB"):
        import_font(b"0"*(10*1024*1024+1))


def test_tolerance_and_zip_contain_round_trippable_separate_parts():
    p = Project()
    parts = tolerance_parts(p)
    assert len(parts) == 8 and all(x.mesh.is_volume for x in parts)
    with zipfile.ZipFile(io.BytesIO(tolerance_zip(p))) as z:
        assert len([n for n in z.namelist() if n.endswith(".stl")]) == 8
        assert len(read_3mf(z.read("TOLERANCE_PRINT.3mf"))) == 8
    r = generate(p)
    with zipfile.ZipFile(io.BytesIO(project_zip(r))) as z:
        assert Project.model_validate_json(z.read("project.json")) == p
        assert len(read_3mf(z.read("ASSEMBLY.3mf"))) == 2
        assert all(trimesh.load(io.BytesIO(z.read(n)), file_type="stl").is_volume for n in z.namelist() if n.endswith(".stl"))


def test_centerline_routes_split_branches_and_report_unsafe_geometry():
    p = Project(mode="neon", led={"source": "neon", "auto": True, "width": 6})
    shape = text_shapes(p)[0].shape
    paths, branches = centerlines(shape, p.led)
    assert len(paths) > 2 and branches > 0
    r = generate(p)
    assert not r.valid
    assert any(i.code in ("neon_radius", "neon_cut", "neon_branch") for i in r.issues)


def test_unsafe_parameter_values_and_nonfinite_neon_coordinates_are_rejected():
    from pydantic import ValidationError
    for kwargs in ({"wall": 0}, {"depth": 3}, {"clearance": 2}, {"text": "   "}, {"height": float("nan")}, {"printer": [1, 180, 180]}):
        with pytest.raises(ValidationError):
            Project(**kwargs)
    with pytest.raises(ValidationError):
        NeonPath(id="nan", points=[(0, 0), (float("nan"), 3)])
