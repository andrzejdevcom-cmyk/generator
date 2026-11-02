from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Placement(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    kind: Literal["strip", "pcb", "wire", "screw", "keyhole", "magnet", "standoff", "cable", "connector"] = "strip"
    x: float = Field(default=0, ge=-5000, le=5000)
    y: float = Field(default=0, ge=-5000, le=5000)
    angle: float = Field(default=0, ge=-360, le=360)
    length: float = Field(default=30, gt=0, le=1000)
    width: float = Field(default=10, gt=0, le=200)
    height: float = Field(default=2, gt=0, le=200)
    diameter: float = Field(default=5, ge=1, le=100)
    mounting_points: int = Field(default=4, ge=2, le=12)
    fixing: Literal["adhesive", "guides", "holders"] = "guides"
    wire_exit: Literal["start", "end", "back"] = "end"


class NeonPath(StrictModel):
    id: str = Field(max_length=64)
    points: list[tuple[float, float]] = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def bounded(self):
        import math
        if any(not math.isfinite(v) or abs(v) > 5000 for p in self.points for v in p):
            raise ValueError("Współrzędne ścieżki muszą być skończone i mieścić się w ±5000 mm.")
        return self


class LedConfig(StrictModel):
    source: Literal["strip", "cob", "pcb", "neon"] = "strip"
    width: float = Field(default=10, ge=1, le=100)
    height: float = Field(default=2, ge=0.5, le=100)
    pcb_length: float = Field(default=30, ge=3, le=1000)
    mounting_points: int = Field(default=4, ge=2, le=12)
    fixing: Literal["adhesive", "guides", "holders"] = "guides"
    wire_exit: Literal["start", "end", "back"] = "end"
    watts_per_m: float = Field(default=9.6, ge=0, le=200)
    voltage: Literal[5, 12, 24, 48] = 12
    auto: bool = False
    placements: list[Placement] = Field(default_factory=list, max_length=150)
    neon_paths: list[NeonPath] = Field(default_factory=list, max_length=100)
    seat_depth: float = Field(default=5, ge=1, le=100)
    clearance: float = Field(default=0.3, ge=0.05, le=2)
    min_radius: float = Field(default=15, ge=1, le=200)
    bend_direction: Literal["side", "top"] = "side"
    cut_length: float = Field(default=25, ge=1, le=1000)


class Project(StrictModel):
    schema_version: Literal[1] = 1
    name: str = Field(default="Moja litera LED", min_length=1, max_length=100)
    text: str = Field(default="A", min_length=1, max_length=120)
    font_id: str = Field(default="dejavu-sans-bold", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    mode: Literal["solid", "led", "neon"] = "led"
    height: float = Field(default=120, ge=10, le=1000)
    depth: float = Field(default=25, ge=2, le=200)
    width_scale: float = Field(default=100, ge=20, le=300)
    target_width: float | None = Field(default=None, ge=5, le=4000)
    proportional: bool = False
    spacing: float = Field(default=2, ge=-30, le=100)
    line_spacing: float = Field(default=1.3, ge=0.8, le=4)
    joined: bool = False
    base: bool = False
    base_depth: float = Field(default=8, ge=2, le=80)
    base_thickness: float = Field(default=3, ge=1, le=30)
    bridge_accents: bool = False
    bridge_width: float = Field(default=2, ge=0.8, le=10)
    corner_radius: float = Field(default=0, ge=0, le=10)
    wall: float = Field(default=2, ge=0.6, le=15)
    back: float = Field(default=2, ge=0.6, le=15)
    front: float = Field(default=1.2, ge=0.4, le=10)
    clearance: float = Field(default=0.25, ge=0.05, le=2)
    shelf_width: float = Field(default=1, ge=0.4, le=6)
    shelf_thickness: float = Field(default=1.2, ge=0.6, le=8)
    collar: bool = False
    body_color: str = Field(default="#263e40", pattern=r"^#[0-9a-fA-F]{6}$")
    front_color: str = Field(default="#f2e7cd", pattern=r"^#[0-9a-fA-F]{6}$")
    nozzle: float = Field(default=0.4, ge=0.2, le=1.2)
    printer: tuple[float, float, float] = (180, 180, 180)
    segment: bool = False
    segment_size: float = Field(default=160, ge=40, le=400)
    pin_diameter: float = Field(default=3, ge=2, le=8)
    material_density: float = Field(default=1.24, ge=0.5, le=3)
    price_per_kg: float = Field(default=85, ge=0, le=10000)
    led: LedConfig = Field(default_factory=LedConfig)

    @model_validator(mode="after")
    def limits(self):
        for collection in (self.led.placements, self.led.neon_paths):
            if len({item.id for item in collection}) != len(collection):
                raise ValueError("Identyfikatory elementów i tras muszą być unikalne.")
        if not self.text.strip():
            raise ValueError("Wpisz tekst zawierający przynajmniej jeden widoczny znak.")
        if len(self.text.splitlines()) > 6:
            raise ValueError("Maksymalnie 6 wierszy tekstu.")
        if any(not 40 <= v <= 2000 for v in self.printer):
            raise ValueError("Pole robocze drukarki: 40–2000 mm na każdej osi.")
        if self.mode == "led" and self.back + self.front + self.shelf_thickness >= self.depth:
            raise ValueError("Głębokość musi pomieścić tył, komorę LED, półkę i front.")
        if self.mode == "led" and self.clearance >= self.shelf_width:
            raise ValueError("Luz na stronę musi być mniejszy od szerokości półki.")
        if self.mode == "neon" and self.led.seat_depth + self.back >= self.depth:
            raise ValueError("Rowek Neon Flex musi pozostawić pełną tylną ściankę.")
        return self


class Issue(StrictModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    element_id: str | None = None
