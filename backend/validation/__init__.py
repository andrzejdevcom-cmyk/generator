import numpy as np

from backend.models import Issue


def validate_parts(project, parts):
    issues = []
    for part in parts:
        m = part.mesh
        if not part.printable:
            continue
        if not m.is_watertight or not m.is_winding_consistent or m.volume <= 0:
            issues.append(Issue(severity="error", code="invalid_mesh", element_id=part.id,
                                message=f"{part.name}: siatka nie jest poprawną zamkniętą bryłą."))
        if not np.isfinite(m.vertices).all() or np.any(m.area_faces < 1e-12):
            issues.append(Issue(severity="error", code="degenerate_mesh", element_id=part.id,
                                message=f"{part.name}: siatka zawiera zdegenerowane trójkąty."))
        extent = m.extents
        # Allow a 90° rotation on the print bed, never pretend splitting occurred.
        fits = ((extent[0] <= project.printer[0]+.01 and extent[1] <= project.printer[1]+.01) or
                (extent[1] <= project.printer[0]+.01 and extent[0] <= project.printer[1]+.01)) and extent[2] <= project.printer[2]+.01
        if not fits:
            issues.append(Issue(severity="warning", code="bed_size", element_id=part.id,
                                message=f"{part.name}: {extent[0]:.1f} × {extent[1]:.1f} × {extent[2]:.1f} mm przekracza pole drukarki. Włącz podział lub zmień profil."))
        shells = m.split(only_watertight=False)
        if len(shells) > 1:
            issues.append(Issue(severity="info", code="detached", element_id=part.id,
                                message=f"{part.name}: {len(shells)} oddzielnych brył (np. akcenty/kropki). Włącz łączniki znaków, jeśli mają tworzyć jedną część."))
        for shell in shells:
            if shell.volume < 1 or min(sorted(shell.extents)[:2]) < project.nozzle*1.5:
                issues.append(Issue(severity="warning", code="small_island", element_id=part.id,
                                    message=f"{part.name}: drobny element wymaga sprawdzenia względem dyszy {project.nozzle:g} mm."))
                break
    if project.mode == "led":
        if project.wall < project.nozzle*2 or project.back < project.nozzle*2:
            issues.append(Issue(severity="warning", code="thin_wall", message="Ścianka lub tył ma mniej niż dwie szerokości dyszy."))
        if project.front < project.nozzle*2:
            issues.append(Issue(severity="warning", code="thin_front", message="Dyfuzor jest cieńszy niż dwie szerokości dyszy; dobierz warstwy i materiał."))
        issues.append(Issue(severity="warning", code="heat", message="Sprawdź odprowadzanie ciepła LED, dopuszczalną temperaturę filamentu i rzeczywiste luzy po wydruku. Symulacja światła jest poglądowa."))
    return issues
