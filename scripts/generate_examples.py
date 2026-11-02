"""Regenerate the checked, editable sample projects and fabrication files."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.export.files import project_zip, three_mf
from backend.geometry.engine import generate
from backend.geometry.tolerance import tolerance_zip
from backend.models import NeonPath, Placement, Project
from backend.geometry.text import text_shapes


def write_example(name, project):
    result = generate(project)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]
    assert all(p.mesh.is_volume for p in result.parts)
    folder = ROOT / "examples" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(project.model_dump_json(indent=2), "utf-8")
    (folder / f"{name}.zip").write_bytes(project_zip(result))
    (folder / f"{name}_ASSEMBLY.3mf").write_bytes(three_mf(result.parts))
    for part in result.parts:
        if part.printable:
            mesh = part.mesh.copy()
            mesh.apply_translation(-mesh.bounds[0])
            filename = ("A_BODY" if part.kind == "body" else "A_DIFFUSER") if name == "A_LED_120" else part.name
            (folder / f"{filename}.stl").write_bytes(mesh.export(file_type="stl"))
    (folder / "validation.json").write_text(json.dumps(result.response(include_mesh=False), ensure_ascii=False, indent=2), "utf-8")
    print(name, "OK", len(result.parts), "parts", [round(v, 2) for v in result.stats["dimensions"]])
    return result


def main():
    from backend.led.layout import placement_envelope
    from shapely.ops import unary_union
    p = Project(name="A 120 mm — PCB 10 × 30 mm", led={"source": "pcb", "width": 10, "height": 2,
                 "pcb_length": 30, "fixing": "holders", "mounting_points": 4, "auto": True})
    proposed = generate(p)
    assert proposed.placements
    pcb = proposed.placements[0]
    region = proposed.cavity.buffer(-3).difference(placement_envelope(pcb, 0).buffer(4))
    q = region.representative_point()
    wire = Placement(id="wire-exit", kind="wire", x=q.x, y=q.y, diameter=5)
    p.led.auto = False
    p.led.placements = [pcb, wire]
    write_example("A_LED_120", p)
    (ROOT / "examples" / "TOLERANCE.zip").write_bytes(tolerance_zip(p))
    write_example("3DAS_SOLID", Project(name="3DAS — pełne litery", text="3DAS", mode="solid", height=80))
    write_example("POLSKIE_ZOLW", Project(name="ŻÓŁW — polskie znaki", text="ŻÓŁW", mode="solid", height=80))
    n = Project(name="I — poprawny rowek Neon Flex", text="I", mode="neon", led={"source": "neon", "width": 6, "height": 8, "cut_length": 20})
    shape = text_shapes(n)[0].shape
    cx = (shape.bounds[0]+shape.bounds[2])/2
    n.led.neon_paths = [NeonPath(id="neon-I", points=[(cx, 20), (cx, 100)])]
    write_example("NEON_I", n)
    write_example("I_SEGMENTED", Project(name="I 260 mm — segmenty i łącznik", text="I", height=260, segment=True, segment_size=130))


if __name__ == "__main__":
    main()
