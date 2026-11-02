# Instalacja i uruchamianie

## Wersje

- Python **3.12 x64**, `venv` i pip (Windows: dystrybucja python.org z launcherem `py`).
- Node.js **22 lub 24 LTS**, npm. Instalacja przypięta przez `package-lock.json`.
- Przeglądarka z WebGL2. Bez WebGL pozostaje edytor 2D i eksport.
- Biblioteki są w `requirements.txt`, razem z zależnościami testowymi. `uvloop` ma marker wykluczający Windows.

Brak usług zewnętrznych, kont i API keys. Do instalacji potrzebny jest dostęp do PyPI i registry npm; fonty są już dołączone. W codziennym użyciu aplikacja nie potrzebuje Internetu.

## Windows

Rozpakuj projekt do dowolnego katalogu, np. ze spacjami w nazwie. Uruchom `install.bat`, a potem `start.bat`. Skrypty sprawdzają wersje, tworzą `.venv`, instalują biblioteki, budują Vite i wykonują test brył A. `start.bat` uruchamia FastAPI podającą również gotowy frontend. Przeglądarka otwiera się dopiero po otrzymaniu poprawnego `/api/health`.

Skrypty PowerShell lokalnie używają `-ExecutionPolicy Bypass` dla własnego procesu; nie zmieniają globalnej polityki Windows. Nie wyłączają TLS, weryfikacji pakietów ani kontroli geometrii.

Odpowiednik w PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Wymagana weryfikacja na rzeczywistym Windows: pierwsza instalacja, ponowne uruchomienie, ścieżka ze spacjami, Ctrl+C i program domyślnej przeglądarki. Sprawdzenie dostępności wheeli Windows wykonano w chmurze; nie zastępuje ono testu uruchomienia w Windows.

### Wykrywanie Pythona

Wymagana jest gałąź **3.12, 64-bit**. Python 3.15 nie jest traktowany jako jej zamiennik. Biblioteki geometrii i testy tej wersji projektu są przypięte do sprawdzonego środowiska 3.12.

Jeśli widzisz `py.exe : No suitable Python runtime found`, launcher nie znalazł wymaganej wersji. W terminalu Windows uruchom:

```powershell
winget install --id Python.Python.3.12 --exact
```

Nie musisz usuwać już zainstalowanego 3.15. Jeśli korzystasz z Python Install Manager obsługującego polecenie `install`, możesz zamiast winget wykonać `py install 3.12`. Jeśli nie masz winget ani menedżera, skorzystaj z instalatora Windows x64 dla gałęzi 3.12 na python.org; zaznacz instalację launchera `py` i dodanie Pythona do PATH.

Po instalacji zamknij terminal, otwórz nowy i wykonaj:

```powershell
py -3.12 --version
py -3.12 -c "import struct; print(struct.calcsize('P') * 8)"
```

Oczekiwany wynik to `Python 3.12.x` i `64`. Następnie uruchom `install.bat` ponownie.

Poprawiony instalator sprawdza istniejący `.venv`, standardowe wpisy rejestru, typowe katalogi instalacji, instalacje Python Install Manager, launcher i PATH. Błąd nieudanej próby `py -3.12` nie przerywa kolejnych prób. Komunikat końcowy rozróżnia niewłaściwą wersję, 32-bit i całkowity brak Pythona. Jeśli 3.12 już jest zainstalowany bez PATH, standardowa instalacja powinna zostać odnaleziona przez rejestr lub katalog.

Test logiki wykrywania (PowerShell, z dowolnego systemu z Pythonem 3.12 x64):

```powershell
pwsh -NoProfile -File tests/windows-tools.tests.ps1 -Python python
```

Na Windows można użyć `powershell.exe` zamiast `pwsh`, wskazując w `-Python` ścieżkę do prawdziwego `python.exe` 3.12, również gdy znajduje się w katalogu ze spacjami. Testy symulują procesy z błędami i metadanymi innych wersji, a dodatkowo uruchamiają rzeczywisty interpreter. Nie instalują ani nie usuwają żadnego Pythona.

## Linux / macOS

W katalogu projektu uruchom `bash scripts/install.sh` i `bash scripts/start.sh`. Skrypt oczekuje, że polecenie `python` wskazuje 3.12. Jeśli w systemie jest `python3.12`, utwórz nim `.venv` i wykonaj polecenia ręcznie. Zweryfikowano Linux x64; macOS nie testowano.

Praca developerska: `.venv/bin/python scripts/dev.py` uruchamia API z reload oraz Vite na oddzielnym porcie, z proxy `/api`. Opcja `--no-browser` nie otwiera okna. Ctrl+C sprząta oba uruchomione procesy. Wersja produkcyjna używa jednego procesu API, bez Vite dev server.

## Chmura

Katalog projektu: `/workspace/generator`. Używaj istniejącego checkoutu w izolowanym środowisku; nie twórz worktree bez wyraźnej prośby. Zależności i zbudowany frontend są zachowywane w migawce. Proces serwera trzeba uruchomić w nowym zadaniu ponownie przez `bash scripts/start.sh`.

Do wewnętrznej kontroli użyj lokalnego żądania do `/api/health`, a potem wywołania generowania i eksportu. Sam otwarty port nie dowodzi poprawności geometrii. Bezpieczne testy regresji są opisane w `TESTS.md`. W chmurze zapisywane instrukcje konfiguracji nie publikują środowiska automatycznie; publikacja jest osobnym działaniem w ustawieniach.

## Rozwiązywanie problemów

| Objaw | Działanie |
|---|---|
| Brak Python/Node | Zainstaluj wymagane wersje, otwórz nowy terminal i ponów instalację. |
| `No suitable Python runtime found` / zainstalowany tylko 3.15 | Doinstaluj 3.12 x64 obok obecnej wersji; sprawdź `py -3.12 --version`. |
| Błąd pip/npm | Przeczytaj pierwszy błąd, sprawdź dostęp do PyPI/npm i proxy. Nie wyłączaj TLS. |
| Zajęty port 8000 | Zamknij własną poprzednią instancję. Skrypt nie zabija cudzych procesów. |
| Brak strony po zmianie frontendu | Wykonaj `npm --prefix frontend run build` i zrestartuj API. |
| Brak WebGL | Zaktualizuj przeglądarkę/sterownik; skorzystaj z 2D. |
| Brak fontu w JSON | Zaimportuj dokładnie ten sam TTF/OTF i ponownie otwórz projekt. Nie podmieniaj fontu bez decyzji użytkownika. |
| Czerwona kontrola projektu | Sprawdź szerokość LED, odstępy, grubości i pozycje. Eksport zostaje zablokowany do naprawy. |
| Za mało miejsca na łuk Neon | Rozsuń węzły, powiększ obrys lub wybierz profil o innym dopuszczalnym promieniu. |
| Nie mieści się na stole | Eksport może być geometrycznie poprawny; podziel model albo wybierz większą drukarkę. |

## Testy przeglądarkowe

Zainstaluj Chromium Playwright (`npx playwright install chromium`) lub wskaż istniejący przez `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. Konfiguracja automatycznie wykrywa `/usr/bin/chromium` na Linux. Testy oczekują uruchomionej aplikacji na porcie 8000. Nie używają płatnych usług ani zdalnej przeglądarki.

W tym środowisku pobieranie z cdn.playwright.dev było niedozwolone, dlatego użyto istniejącego systemowego Chromium. Nie zmieniano allowlisty ani nie omijano proxy.
