"""Functional local readiness: served frontend + real generated meshes + strict 3MF read."""
import http.client
import json
import sys
from pathlib import Path

import lib3mf
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.export.files import read_3mf
from backend.models import Project


def call(method, path, body=None):
    # This client is deliberately restricted to the local application, not remote egress.
    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=60)
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=data, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    content = response.read()
    assert response.status == 200, (response.status, content[:500])
    conn.close()
    return content


def main():
    health = json.loads(call("GET", "/api/health"))
    assert health["application"] == "3DAS Letter Maker" and health["status"] == "ok"
    assert b"3DAS Letter Maker" in call("GET", "/")
    project = Project.model_validate_json((ROOT/"examples/A_LED_120/A_LED_120.json").read_text("utf-8"))
    data = project.model_dump(mode="json")
    model = json.loads(call("POST", "/api/generate", data))
    assert model["valid"], model["issues"]
    count = 0
    for part in model["parts"]:
        if part["printable"]:
            mesh = trimesh.Trimesh(part["vertices"], part["faces"], process=True)
            assert mesh.is_volume and mesh.is_watertight and mesh.volume > 0
            count += 1
    assert count == 2 and model["placements"]
    file = call("POST", "/api/export?format=3mf", data)
    assert len(read_3mf(file)) == count
    wrapper = lib3mf.get_wrapper()
    native = wrapper.CreateModel()
    reader = native.QueryReader("3mf")
    reader.SetStrictModeActive(True)
    reader.ReadFromBuffer(file)
    assert reader.GetWarningCount() == 0
    print("OK: frontend, API, A 120 mm, korpus i front jako zamknięte bryły, LED, ścisły odczyt 3MF.")


if __name__ == "__main__":
    main()
