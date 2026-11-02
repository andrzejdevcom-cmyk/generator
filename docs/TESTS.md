# Raport weryfikacji

Środowisko: Linux x64, Python 3.12.14, Node 24.19.0, npm 11.9.0, systemowy Chromium z programowym WebGL. Wersje bibliotek są przypięte w requirements.txt i package-lock.json. Testy wykonano na utworzonym projekcie, nie tylko opisano polecenia.

## Wyniki

- **31 testów pytest — zaliczone**, bez pominiętych/wyłączonych/oczekiwanych błędów.
- **5 scenariuszy Playwright — zaliczone**: rzeczywisty Canvas/WebGL, PNG i pobranie ZIP/3MF/STL, ręczna edycja LED i undo, blokowanie błędnego montażu, zapis/otwarcie JSON, Neon Flex oraz ekran 390 px.
- TypeScript i produkcyjny build Vite — zaliczone. Three.js jest ładowany osobno; Vite zgłasza ostrzeżenie o dużej paczce modułu 3D (~928 kB przed gzip).
- **10 testów wykrywania Pythona — zaliczone w PowerShell 7.4.6 na Linux**: błąd launchera i fallback, 3.15 obok 3.12, wykryta niewłaściwa wersja, 32/64-bit, nieistniejący proces, ścieżki ze spacjami, prawdziwy interpreter 3.12, brak instalacji i parsowanie skryptów. To test logiki PowerShell i natywnych wywołań, nie pełna instalacja na Windows/PowerShell 5.1.
- Pełny `bash scripts/install.sh` wykonany ponownie — zaliczony; npm ci i test rzeczywistych brył A przeszły.
- Ponowny start przez `bash scripts/start.sh` oraz `scripts/smoke.py` — zaliczone: strona, identyfikacja API, kompletne bryły przykładowej A, montaż LED, ponowny odczyt pobranego 3MF.
- `pip check` — brak uszkodzonych zależności.
- Pobranie wszystkich przypiętych wheeli dla Windows x64 / CPython 3.12 — zaliczone (uvloop jest wyłączony markerem Windows). To kontrola dostępności pakietów, nie uruchomienie w Windows.
- Import CFF/OTF sprawdzony dodatkowo na systemowym Nimbus Sans Bold: A/B/O jako zamknięte bryły. Font testowy nie jest dołączony do aplikacji; dołączone są licencjonowane DejaVu TTF.

## Obowiązkowe przypadki

| # | Przypadek | Sprawdzenie rzeczywistej zawartości |
|---|---|---|
| 1 | A | 1 otwór w obrysie, pustka w bryle w jego wnętrzu, zgodność objętości z polem × Z |
| 2 | B | 2 otwory, oba zachowane w wyciągnięciu |
| 3 | O | 1 otwór, pusty środek, zamknięta siatka |
| 4 | Ł | kreska zmienia pole/kontur względem L; bryła jest poprawna |
| 5 | ŻÓŁW | 4 glify, akcenty Ż i Ó zachowane jako oddzielne bryły |
| 6 | 3DAS | osobne części, skala XY, realny kerning HarfBuzz AV i dodatkowy odstęp |
| 7 | A LED | materiał w dnie, brak materiału w komorze na właściwym Z, front, prowadnice i miejsce na 10 mm |
| 8 | za szeroki LED | błąd obrysu z wymiarami, eksport API i przyciski blokowane |
| 9 | ścianka 2 → 3 | wzrost objętości korpusu i spadek pola komory/objętości dyfuzora |
| 10 | STL/3MF | ponowny odczyt, zamknięcie/objętość, zgodne wymiary i liczba obiektów; lib3mf strict bez ostrzeżeń |
| 11 | JSON | równe wszystkie parametry, identyczne siatki po odtworzeniu; także zapis serwera i przeglądarki |
| 12 | A1 mini | ostrzeżenie dla zbyt wysokiej części, rzeczywisty podział I 260 mm, gniazda/kołki bez kolizji |
| 13 | front/półka | pomiar luzu 0,25 mm, dodatnia powierzchnia podparcia, zerowa wspólna objętość brył |
| 14 | PCB | rzeczywiste XYZ listwy, cztery podstawki, otwarte otwory i materiał wokół nich |
| 15 | Neon | odrzucenie ostrych zakrętów i złego cięcia; poprawny rowek faktycznie usuwa materiał tylko na zadaną głębokość |

Dodatkowo: ślepe kieszenie/kanały, keyhole i otwory, przelot przez dodatkową podstawę, pozycjonujący kołnierz, mostki akcentów i liter, integralna płyta tylna, różne geometrie prowadnic/uchwytów, PCB klejone do dna bez lewitowania, odrzucenie zbyt gęstych otworów PCB, zbyt małe akcenty, brakujący font/znaki, SHA-256 fontu, limity importu, unikalne ID, NaN, graf rozgałęzień, kompletność ZIP i czterech testów luzu.

## Rozpoznane i poprawione problemy

Pierwszy triangulator tworzył niepoprawne pionowe krawędzie przy niektórych offsetach B/D i keyhole. Wyciąganie przeniesiono do CrossSection Manifold z regułą EvenOdd. Testy geometrii i kolizji ponownie przeszły, bez wyłączania asercji.

Otwory przelotowe początkowo kończyły się na dnie litery po włączeniu dodatkowej płyty. Różnica jest teraz stosowana do całej zintegrowanej bryły, a test bada pustkę także w ujemnym Z płyty. PCB klejone jest na dnie; podniesienie 2 mm dotyczy tylko podstawek.

Instalator Windows przerywał wykrywanie przy `py -3.12`, gdy launcher zgłaszał `No suitable Python runtime found`: ustawienie `Stop` zmieniało stderr w `NativeCommandError` przed dalszymi próbami i wyjaśnieniem. Próby interpretera mają teraz lokalną obsługę niepowodzenia, a końcowy komunikat pokazuje wykryte wersje i sposób doinstalowania 3.12. Weryfikowana jest także architektura 64-bit. Entry pointy pokazują czytelny komunikat zamiast stosu wyjątku.

Ostrzeżenia wykonania testów: zależność Starlette zgłasza deprecjację aliasu AnyIO; trimesh zgłasza dzielenie przez zerową objętość przy mierzeniu pustego wyniku przecięcia brył w testach kolizji. Te przecięcia mają być puste; nie są eksportowanymi częściami. Nie wyłączano walidacji ani testów, aby uzyskać wynik dodatni.

## Co wymaga dalszej weryfikacji

- Windows: rzeczywiste uruchomienie BAT/PowerShell, ścieżka ze spacjami, otwarcie domyślnej przeglądarki i zamknięcie procesu.
- OrcaSlicer/Bambu Studio: import każdego typu 3MF i STL, odrębność części/kolorów, orientacja, slicing i plan stołów. Nie deklarujemy tej zgodności na podstawie samego lib3mf.
- Wydruki: cztery luzy testowe, półka i kołnierz, gniazda/kołki, podstawki PCB, keyhole i nośność, temperatury LED, wentylacja i skurcz materiałów.
- Neon: rzeczywisty profil i kierunek gięcia producenta, cięcie, wyprowadzenia przewodów oraz krzywizna w płaszczyźnie. Aproksymacja szkieletu nie zastępuje próby montażowej.
- Nie ma solvera fotometrycznego, automatycznego doboru zasilacza, profilu AMS, ogólnego analizatora termicznego ani dowodu drukowalności w każdym slicerze.

Wyniki sprawdzają gotowość lokalnej instalacji i wygenerowane pliki. Zapis konfiguracji chmurowej nie jest publikacją ani dowodem odtworzenia migawki w nowym zadaniu.
