# Sprawdzone przykłady

Każdy katalog zawiera kompletny projekt JSON do otwarcia w aplikacji, osobne STL, złożenie 3MF, ZIP z układem do druku i `validation.json`. Wygeneruj ponownie poleceniem `.venv/bin/python scripts/generate_examples.py`.

| Projekt | Zawartość |
|---|---|
| `A_LED_120` | A: wysokość 120, głębokość 25, ścianki/tył 2, dyfuzor 1,2, luz 0,25; PCB 10 × 30 × 2 mm, podstawki i ograniczniki, przelot przewodu Ø5 |
| `3DAS_SOLID` | osobne pełne litery 3DAS, wysokość H 80, głębokość 25 |
| `POLSKIE_ZOLW` | polskie znaki ŻÓŁW, oddzielne akcenty zachowane |
| `NEON_I` | poprawna prosta trasa Neon Flex 80 mm, szerokość 6, wysokość profilu 8, cięcie co 20, rowek 5 głębokości |
| `I_SEGMENTED` | I 260 mm: segmenty 130 mm, ślepe gniazda i osobny łącznik dwukołkowy |
| `TOLERANCE.zip` | 4 pary korpus–front: 0,15/0,25/0,35/0,45 mm na stronę; STL, 3MF i instrukcja |

Pliki STL są znormalizowane do Z=0 i nie zawierają kolorów. W 3MF złożenia dyfuzor znajduje się na górze korpusu; do druku użyj osobnych STL lub PRINT_LAYOUT. Złożenie referencyjne z elektroniką jest osobnym plikiem **DO_NOT_PRINT** wewnątrz ZIP.

To cyfrowo sprawdzone modele, bez fizycznych prób. Najpierw przetestuj luzy, gniazda, mocowanie listwy i otwory. Nie potwierdzono importu w OrcaSlicer ani Bambu Studio.
