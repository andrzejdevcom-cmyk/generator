# Parametry projektu

Wszystkie odległości są w milimetrach, chyba że pole ma inną jednostkę. Dokładne limity i domyślne wartości są w `backend/models.py`; poniżej opis znaczenia pól.

| Pole | Znaczenie / domyślnie |
|---|---|
| `schema_version` | 1; inna wersja projektu jest odrzucana |
| `text`, `font_id` | tekst do 120 znaków/6 wierszy, identyfikator konkretnego fontu |
| `mode` | `solid`, `led`, `neon` |
| `height` | wysokość wielkiej litery H w XY, 120 |
| `depth` | wysokość drukowania w osi Z, 25 |
| `width_scale` | niezależne skalowanie X, 100% |
| `target_width` | zadana szerokość całego widocznego napisu lub null |
| `proportional` | przy zadanej szerokości skaluje także wysokość XY |
| `spacing`, `line_spacing` | dodatkowy odstęp znaków 2 mm; odległość baz wierszy 1,3 × wysokość H |
| `joined`, `bridge_width` | mostki pomiędzy literami, szerokość 2 |
| `bridge_accents` | mostki pomiędzy oddzielnymi elementami glifu |
| `base`, `base_depth`, `base_thickness` | wspólna pełna płyta od tyłu; całkowity naddatek XY 8 (4 na stronę); grubość 3 |
| `corner_radius` | zaokrąglanie obrysu XY, 0; zanikanie >20% pola lub wysp odrzuca zmianę |
| `wall`, `back` | ścianka boczna 2; dno 2 |
| `front`, `clearance` | dyfuzor 1,2; luz 0,25 **na stronę** |
| `shelf_width`, `shelf_thickness` | półka 1 szerokości i 1,2 grubości |
| `collar` | dodatkowy kołnierz 0,8 szerokości, do 1 głębokości, z tym samym luzem |
| `body_color`, `front_color` | kolory podglądu i materiałów bazowych 3MF; STL pozostaje bez materiału |
| `printer` | [X,Y,Z], domyślnie A1 mini [180,180,180] |
| `nozzle` | średnica dyszy 0,4 do ostrzeżeń detali i ścian |
| `segment`, `segment_size`, `pin_diameter` | podział XY; limit 160; kołki 3 |
| `material_density`, `price_per_kg` | 1,24 g/cm³ i 85 zł/kg; koszt pełnej objętości CAD |

## Źródło LED

`led.source`: strip/COB/PCB/neon. Szerokość 10, wysokość 2, PCB długości 30, 4 punkty mocowania. `fixing` wybiera klej/prowadnice/uchwyty. Presety szerokości 8/10/12 mm są skrótami, nie ograniczeniem.

Parametry źródła dotyczą **nowych propozycji i elementów**. Każdy istniejący element zachowuje własne wymiary, mocowanie, kąt i liczbę punktów. Zapobiega to niejawnej zmianie wszystkich części po zmianie presetu. `wire_exit` zapisuje plan wyjścia listwy (start/end/back) w manifeście; rzeczywisty przelot obudowy dodaje się jako osobny element `wire`.

`watts_per_m` domyślnie 9,6 W/m, `voltage` 12 V. Dla PCB podaj liniową moc równoważną. Moc = suma długości sekcji × W/m. Szacunkowy przewód łączy środki LED w kolejności z zapasem 20%, nie uwzględnia dojścia do zasilacza.

## Ręczne elementy

Każdy `Placement` ma stabilne `id`, `x`, `y`, `angle`, `length`, `width`, `height`, `diameter`, `mounting_points`, `fixing`, `wire_exit`. Współrzędne są liczone względem lewego dolnego rogu widocznego obrysu napisu; X w prawo, Y w górę. Obrót w stopniach, wokół środka elementu.

| `kind` | Wykonanie |
|---|---|
| strip | referencja taśmy, opcjonalne boczne prowadnice/uchwyty |
| pcb | rzeczywiste podstawki i otwory, referencja PCB z pasującymi otworami |
| wire / screw | okrągły przelot o zadanej średnicy |
| keyhole | przelot z kołem i węższym pionowym slotem; obrót dotyczy całego kształtu |
| magnet | ślepa okrągła kieszeń; `height` oznacza głębokość od wnętrza |
| standoff | integralny dystans o średnicy zewnętrznej `diameter + 4`; otwór przelotowy |
| cable | prostokątny kanał, `height` oznacza głębokość od wnętrza dna |
| connector | miejsce na złączkę z dwiema ścianami bocznymi i bryłą referencyjną |

Otwór przewodu podaje się średnicą (domyślnie 5); długość/szerokość są używane dla elementów prostokątnych. Głębokość kieszeni/kanału musi pozostawić min. 0,6 mm dna. Stosowanie większych otworów wymaga materiału na całym obwodzie. Za szeroki LED nie jest automatycznie pomniejszany.

## Neon Flex

`width` szerokość profilu, `height` wysokość profilu, `seat_depth` głębokość rowka 5, `clearance` 0,3 na stronę, `min_radius` 15, `bend_direction` side/top, `cut_length` 25. Obsługiwane trasy są płaskie z gięciem bocznym. Trasa `NeonPath` to `id` i uporządkowane punkty [x,y].

Zaokrąglanie dodaje punkty rzeczywistego łuku kołowego. Cięcie ma tolerancję długości 0,15 mm. Nie każda automatyczna trasa jest wykonalna; błędy pozostają jawne i wymagają edycji. Przykładowa poprawna trasa dla I znajduje się w `examples/NEON_I`.
