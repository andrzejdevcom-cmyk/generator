import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import backend.main as api
from backend.main import app
from backend.models import Project


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATA", tmp_path)
    with TestClient(app) as c:
        yield c


def test_api_generates_actual_meshes_and_downloads(client):
    p = Project().model_dump(mode="json")
    response = client.post("/api/generate", json=p)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] and len(data["parts"]) == 2
    assert all(len(x["vertices"]) > 10 and x["volume_mm3"] > 0 and x["watertight"] for x in data["parts"])
    validation = client.post("/api/validate", json=p).json()
    assert validation["valid"] and "vertices" not in validation["parts"][0]
    response = client.post("/api/export?format=zip", json=p)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert "project.json" in z.namelist() and "ASSEMBLY.3mf" in z.namelist()


def test_api_blocks_invalid_export_and_missing_fonts(client):
    p = Project(led={"placements": [{"id": "bad", "width": 80}]}).model_dump(mode="json")
    assert not client.post("/api/generate", json=p).json()["valid"]
    assert client.post("/api/export?format=3mf", json=p).status_code == 422
    p["font_id"] = "missing-font"
    res = client.post("/api/generate", json=p)
    assert res.status_code == 422 and "font" in res.json()["detail"]
    assert client.post("/api/export?format=fake", json=p).status_code == 422


def test_api_project_persistence_exact_parameters_and_path_validation(client):
    p = Project(text="ŻÓŁW", name="Zapis i odczyt").model_dump(mode="json")
    saved = client.post("/api/projects", json=p).json()
    assert client.get("/api/projects/"+saved["id"]).json() == p
    assert client.get("/api/projects").json()[0]["name"] == p["name"]
    assert client.get("/api/projects/not-a-uuid").status_code == 404
    assert client.post("/api/project/validate", json=p).json() == p


def test_api_font_rejects_nonfont_and_oversize(client):
    assert len(client.get("/api/fonts").json()) >= 3
    assert client.post("/api/fonts", files={"file": ("bad.ttf", b"INVALID")}).status_code == 422
    assert client.post("/api/fonts", files={"file": ("large.ttf", b"x"*(10*1024*1024+1))}).status_code == 422


def test_api_automatic_led_proposal_and_tolerance_files(client):
    p = Project().model_dump(mode="json")
    res = client.post("/api/led/suggest", json=p)
    assert res.status_code == 200 and len(res.json()["placements"]) > 0
    res = client.post("/api/tolerance", json=p)
    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        assert "TOLERANCE_PRINT.3mf" in z.namelist()
