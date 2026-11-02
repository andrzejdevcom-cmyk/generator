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
