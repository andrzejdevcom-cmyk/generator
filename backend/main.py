import hashlib
import json
import logging
import os
import threading
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from shapely.geometry import LineString

from backend.export.files import project_zip, stl_bytes, three_mf
from backend.fonts import USER_FONTS, import_font, list_fonts, resolve_font
from backend.geometry.engine import generate
from backend.geometry.text import clean, text_shapes
from backend.geometry.tolerance import tolerance_zip
from backend.led.layout import suggest_placements
from backend.led.neon import centerlines, fillet_path
from backend.models import NeonPath, Project
from shapely.ops import unary_union
from shapely.ops import substring

ROOT = Path(__file__).resolve().parents[1]
DATA = USER_FONTS.parent / "projects"
app = FastAPI(title="3DAS Letter Maker", version="1.0.0")
cache = OrderedDict()
lock = threading.RLock()
log = logging.getLogger(__name__)


def generated(project):
    key = hashlib.sha256(project.model_dump_json().encode()).hexdigest()
    with lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        try:
            result = generate(project)
            if sum(len(p.mesh.vertices) for p in result.parts) > 400000:
                raise ValueError("Projekt przekracza limit 400 000 wierzchołków. Skróć tekst lub podziel projekt.")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            log.exception("Geometry generation failed")
            raise HTTPException(422, "Nie udało się zbudować poprawnej geometrii. Zmień font, wymiary lub rozmieszczenie.") from exc
        cache[key] = result
        while len(cache) > 4:
            cache.popitem(last=False)
        return result


@app.get("/api/health")
def health():
    return {"status": "ok", "application": "3DAS Letter Maker", "units": "mm", "version": "1.0.0"}


@app.get("/api/fonts")
def fonts():
    return list_fonts()


@app.post("/api/fonts")
async def upload_font(file: UploadFile = File(...)):
    data = await file.read(10*1024*1024+1)
    try:
        with lock:
            return import_font(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/generate")
def generate_model(project: Project):
    return generated(project).response()


@app.post("/api/validate")
def validate(project: Project):
    return generated(project).response(include_mesh=False)


@app.post("/api/led/suggest")
def suggest(project: Project):
    if project.mode != "led":
        raise HTTPException(422, "Automatyczne rozmieszczenie wymaga trybu kasetonowego.")
    result = generated(project.model_copy(update={"led": project.led.model_copy(update={"auto": True, "placements": []})}))
    return {"placements": [p.model_dump() for p in result.placements], "issues": [i.model_dump() for i in result.issues]}


@app.post("/api/neon/route")
def route(project: Project):
    result = generated(project.model_copy(update={"mode": "neon", "led": project.led.model_copy(update={"auto": True, "neon_paths": []})}))
    return {"paths": [p.model_dump() for p in result.paths], "issues": [i.model_dump() for i in result.issues]}


@app.post("/api/neon/fillet")
def fillet(project: Project):
    try:
        paths = [fillet_path(p, project.led.min_radius) for p in project.led.neon_paths]
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"paths": [p.model_dump() for p in paths]}


@app.post("/api/neon/trim")
def trim(project: Project):
    paths = []
    for p in project.led.neon_paths:
        line = LineString(p.points)
        length = int((line.length+.001)/project.led.cut_length)*project.led.cut_length
        if length < project.led.cut_length:
            raise HTTPException(422, f"Trasa {p.id} jest krótsza od jednej sekcji cięcia.")
        trimmed = substring(line, 0, min(length, line.length))
        paths.append(NeonPath(id=p.id, points=list(trimmed.coords)))
    return {"paths": [p.model_dump() for p in paths]}


@app.post("/api/export")
def export(project: Project, format: Literal["stl", "3mf", "zip"] = "zip", part: str | None = None,
           layout: Literal["assembly", "print"] = "assembly"):
    result = generated(project)
    if not result.valid:
        raise HTTPException(422, "Eksport zablokowany: popraw błędy geometrii lub montażu.")
    selected = [p for p in result.parts if p.printable and (part is None or p.id == part)]
    if not selected:
        raise HTTPException(404, "Nie znaleziono części do eksportu.")
    if format == "zip":
        data = project_zip(result)
    elif format == "3mf":
        data = three_mf(selected, layout, project.printer[0])
    else:
        data = stl_bytes(selected, project.printer[0])
    return Response(data, media_type={"zip": "application/zip", "stl": "model/stl", "3mf": "model/3mf"}[format],
                    headers={"Content-Disposition": f'attachment; filename="3DAS.{format}"'})


@app.post("/api/tolerance")
def tolerance(project: Project):
    try:
        data = tolerance_zip(project)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(data, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="3DAS_TOLERANCE.zip"'})


@app.post("/api/project/validate")
def validate_project(project: Project):
    try:
        resolve_font(project.font_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return project


def project_file(project_id):
    try:
        if str(uuid.UUID(project_id)) != project_id:
            raise ValueError()
    except ValueError as exc:
        raise HTTPException(404, "Nie znaleziono projektu.") from exc
    return DATA / f"{project_id}.json"


@app.get("/api/projects")
def projects():
    if not DATA.exists():
        return []
    found = []
    for p in sorted(DATA.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:50]:
        try:
            value = Project.model_validate_json(p.read_text("utf-8"))
            found.append({"id": p.stem, "name": value.name, "text": value.text, "modified": p.stat().st_mtime})
        except (ValueError, OSError):
            continue
    return found


@app.post("/api/projects")
def save_project(project: Project):
    DATA.mkdir(parents=True, exist_ok=True)
    project_id = str(uuid.uuid4())
    path = project_file(project_id)
    path.write_text(project.model_dump_json(indent=2), "utf-8")
    return {"id": project_id, "name": project.name}


@app.get("/api/projects/{project_id}")
def open_project(project_id: str):
    path = project_file(project_id)
    if not path.is_file():
        raise HTTPException(404, "Nie znaleziono projektu.")
    return Project.model_validate_json(path.read_text("utf-8"))


# A production Vite build is served from the same local origin as the API.
dist = ROOT / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
