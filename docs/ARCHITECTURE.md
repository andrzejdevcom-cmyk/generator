# Architektura i kontrakt geometrii

## Przepływ

```text
React / Project JSON
        ↓ FastAPI + Pydantic (limity, brak NaN, unikalne identyfikatory)
FontTools + HarfBuzz (font, glify, kerning, pozycje)
        ↓ adaptacyjne podziały krzywych Béziera
Shapely (non-zero winding, otwory, offsety, rozłożenie LED)
        ↓ przekroje Manifold / Clipper2
Manifold3D + trimesh (wyciąganie, suma, odejmowanie, cięcia)
        ↓ walidacja, dane części w mm
te same vertices/faces → Three.js / STL / 3MF / ZIP
```

`backend/models.py` jest wersjonowanym kontraktem projektu. Stan projektu zawiera wszystkie parametry wykonawcze, pozycje elementów i węzły tras. Kamera, podświetlenie, motyw i filtr widoku są ustawieniami prezentacji, a nie innym modelem CAD.

## Obrysy i fonty

HarfBuzz pozycjonuje glify ze skalą unitsPerEm, fontTools odczytuje obrysy TrueType/CFF i kompozyty. `FlattenPen` adaptacyjnie dzieli krzywe (nominalny błąd 0,04 mm przed dodatkowym skalowaniem szerokości; limit rekurencji 14). Polygonizacja i liczba nawinięć zachowują otwory oraz nakładające się kontury glifów złożonych. Nie używamy wyłącznie kierunku obrysu ani wypukłej otoczki.

Wysokość parametru to wielka litera **H** danego fontu. Akcenty, wydłużenia dolne, małe litery i wiele wierszy mają rzeczywiste wymiary raportowane w XYZ. Skalowanie szerokości działa po składzie; zadana szerokość dotyczy całego widocznego obrysu. W trybie proporcjonalnym zmienia też wysokość obrysu. Fizyczne grubości ścianek pozostają w mm.

3 fonty DejaVu i ich licencja są w repozytorium. Identyfikator importowanego fontu to `user-` + SHA-256 jego treści. Projekty nie osadzają pliku fontu: na innym komputerze zaimportuj **ten sam** plik. Nazwa rodziny nie zastępuje identyfikatora.

## Przekrój kasetonu

Niech G oznacza obrys litery, I = offset(G, −wall), S = I − offset(I, −shelf_width), F = offset(I, −clearance).

| Część | Przekrój XY | Przedział Z |
|---|---|---|
| Dno | G | 0 … back |
| Ścianki | G − I | back − 0,01 … depth |
| Półka | S | depth − front − shelf_thickness … depth − front |
| Dyfuzor | F | depth − front … depth |
| Opcjonalny kołnierz | pierścień wewnątrz otworu półki | do 1 mm poniżej dyfuzora |

Przekrycie 0,01 mm scala dno ze ściankami; nie jest luzem montażowym. Luz dyfuzora jest liczony **na stronę**, a pola G/I/F zachowują oryginalne otwory liter. Dyfuzor ma dodatnią powierzchnię podparcia na półce, z korpusem dzieli wyłącznie płaszczyznę styku. Testy mierzą przecięcie brył i rzeczywisty odstęp obrysów.

Podstawowe zamknięcie wymaga kleju. Kołnierz służy pozycjonowaniu, nie jest zatrzaskiem.

## LED i mocowania

Automatyka konserwatywnie szuka prostokątów w komorze, przy 12 kątach i ograniczonej siatce punktów. Pełny obrys LED z luzem i mocowaniami musi należeć do komory. Jest to bezpieczna propozycja, **nie optymalizacja pokrycia światłem ani dowód braku miejsca dla wszystkich możliwych ustawień**. Ręczne pozycje są walidowane tym samym testem.

Taśma/COB: klejenie do dna, dwie ciągłe prowadnice albo krótkie uchwyty boczne. PCB: podniesienie 2 mm i zadana liczba podstawek z otworami Ø1,8 mm; opcja uchwytów dodaje ograniczniki na końcach. W referencji PCB odwzorowane są pasujące otwory. Sposób „klej” osadza PCB bezpośrednio na dnie. Dobierz do rzeczywistej płytki — arbitralne moduły mogą mieć inne rozmieszczenie otworów. Parametr wyjścia przewodu to informacja układu montażowego; przelot w obudowie jest osobnym, edytowalnym elementem „otwór na przewód”.

Prowadnice i podstawki są **scalone z korpusem**, a nie udawane jako oddzielny STL. Elektronika i złączki mają bryły referencyjne z rzeczywistymi wymiarami; nie są częściami do drukowania. ZIP zawiera je wyłącznie w `REFERENCE_DO_NOT_PRINT.3mf` i opisuje w `assembly.json`. W złożeniu do druku pozostają korpusy, fronty i łączniki.

Otwory to operacje różnicy brył. Otwory przelotowe przechodzą także przez dodatkową tylną płytę. Kieszenie magnesów i kanały kablowe są ślepe, z min. 0,6 mm dna. Dystans to integralny słupek z otworem. Sloty keyhole obracają się wraz z elementem.

## Neon Flex

Maska obrysu jest rasteryzowana z rozdzielczością min. 0,6 mm, z dłuższym wymiarem ograniczonym do około 550 próbek. Skeletonize tworzy szkielet medialny; graf jest śledzony w oddzielne odcinki przy węzłach o stopniu różnym od 2. To przybliżenie linii środkowej, nie krzywa produkcyjna gotowa dla dowolnego fontu.

Użytkownik ma edytować węzły, rozdzielić skrzyżowania i dodać styczne łuki. Zaokrąglanie konstruuje rzeczywiste łuki kołowe próbkowane maksymalnie co 5°. Gdy promień nie mieści się między węzłami, operacja odmawia zmiany zamiast go zmniejszać. Krótkie odcinki nie są automatycznie kasowane. Wymagane jest gięcie boczne w XY; pionowe jest jawnie odrzucone.

Kontrola promienia bada kolejne próbki. Załamania polilinii większe niż 12° są ostrym narożem (promień 0); gęsto próbkowane łuki są mierzone przez okrąg opisany. Parametr cięcia dotyczy długości linii środkowej, z tolerancją 0,15 mm. „Skróć do cięcia” obcina koniec do najbliższej niższej wielokrotności; pozostawia przebieg łuków. Przecięcia, kolizje rowków, brak wymaganej ścianki i zła długość blokują eksport. Niewykonalne rowki **nie są odejmowane** w podglądzie; błędny projekt pokazuje komunikaty i ścieżki w 2D.

## Segmentacja

Podział w XY na prostokątne segmenty, o wymiarze nie większym niż ustawiony limit i stół drukarki minus 8 mm. W korpusie powstają ślepe gniazda od tyłu, a osobny łącznik ma dwa kołki z luzem na stronę. Płyta łącznika zwiększa grubość od tyłu o 2 mm. Fronty po podziale trzeba wkleić na półki.

Cięcie w obszarze mocowań jest blokowane. Przy braku materiału na wsparty łącznik projekt pozostaje błędny; generator nie obiecuje rozwiązania dla każdego kroju. Podział dodatkowej tylnej płyty jest nieobsługiwany i blokowany. Rozmieszczenie cięć to siatka, bez optymalizatora szwów; zmień rozmiar segmentu, aby zmienić przebieg cięcia.

## Eksport

- STL binarny, pojedyncza część przesunięta do początku, tyłem na stole. Zbiorczy STL układa części w rzędach; nie scala ich i nie przypisuje materiału.
- 3MF Core: OPC ZIP, `[Content_Types].xml`, relacja do `3D/3dmodel.model`, jednostka `millimeter`, osobne zasoby siatek i elementy build, `basematerials` z kolorami RGBA. To **nie profil slicera ani AMS**.
- 3MF złożenia zachowuje współrzędne montażowe. PRINT_LAYOUT normalizuje Z i rozkłada części; nie jest automatycznym nestingiem ani wielopłytowym projektem slicera. Wybierz obiekty na pojedyncze zadania.
- ZIP zawiera osobne STL, oba układy 3MF, JSON projektu i manifest montażu. Elektronika referencyjna ma osobny plik „DO_NOT_PRINT”.
- Format weryfikują własny czytnik Core, trimesh i lib3mf w trybie ścisłym.

## API

| Metoda i ścieżka | Funkcja |
|---|---|
| GET `/api/health` | gotowość i identyfikacja aplikacji |
| GET/POST `/api/fonts` | lista / import TTF i OTF |
| POST `/api/generate` | kompletny Project → części, siatki, obrysy, raport |
| POST `/api/validate` | to samo bez tablic wierzchołków i ścian |
| POST `/api/led/suggest` | bezpieczne propozycje sekcji LED |
| POST `/api/neon/route` | linie środkowe i raport |
| POST `/api/neon/fillet` | styczne łuki dla aktualnych tras |
| POST `/api/neon/trim` | skrócenie do długości cięcia |
| POST `/api/export?format=stl\|3mf\|zip` | eksport poprawnego projektu; `part` wybiera pojedynczą część; `layout=assembly\|print` |
| POST `/api/tolerance` | 4 zestawy luzów w ZIP |
| POST `/api/project/validate` | sprawdzenie schematu i dostępności fontu |
| GET/POST `/api/projects` | ostatnie projekty / nowy zapis |
| GET `/api/projects/{uuid}` | projekt do ponownego otwarcia |

API wymaga pełnego Project JSON, z domyślnymi wartościami z modelu Pydantic. Błędy wejścia/geometrii zwracają 422 z komunikatem. Wygenerowana ale błędna konfiguracja daje `valid:false` i raport, natomiast eksport zwraca 422. Sam status 200 generowania nie potwierdza wykonalności.

## Lokalne dane i granice bezpieczeństwa

Pliki użytkownika: `.local/fonts`, `.local/projects` (można zmienić katalog przez `LETTER_MAKER_DATA`). Ścieżki projektów to wyłącznie poprawne UUID, a fonty są identyfikowane SHA-256. Limit importu fontu 10 MB, projektu z interfejsu 2 MB, 120 znaków / 6 wierszy, 150 elementów LED / 100 tras. Nie wykonujemy poleceń z nazw plików. Fonty są parsowane, bez wykonywania osadzonych programów zewnętrznych.

Generowanie jest serializowane blokadą i buforuje cztery ostatnie modele. Nie ma sieciowej bazy danych. Backend binduje wyłącznie do loopback i nie ustawia otwartego CORS. Wdrożenie internetowe wymaga osobnego zadania: uwierzytelniania, izolacji parsera fontów w procesach, limitów żądań/CPU/pamięci, kolejki zadań i trwałego magazynu plików. Ta wersja jest aplikacją lokalną, nie publiczną usługą wieloużytkownikową.
