# Instrukcja użytkownika

## Projektowanie

Górny pasek zawiera nazwę projektu, ostatnie projekty, instrukcję, zmianę motywu, zapis i przejście do eksportu. W lewym panelu są cztery zakładki: Tekst, Wymiary, LED, Eksport. Mniej typowe ustawienia są rozwijane.

W Tekst wybierz pełną literę, kaseton albo Neon Flex. Wpisz napis; polskie znaki i nowe wiersze są obsługiwane. DejaVu Sans Bold jest zalecany na pierwszy kaseton — cienkie szeryfy innych krojów mogą nie pomieścić komory. Import TTF/OTF nie podmienia brakujących znaków po cichu; komunikat wymienia brakujące znaki.

Wysokość parametryczna odpowiada wielkiej H. Akcenty i wydłużenia mogą zwiększyć rzeczywisty wymiar XYZ. Ustaw szerokość napisu w Wymiary, aby dopasować całość do przestrzeni. „Proporcjonalnie” zmienia też wysokość obrysu; fizyczne grubości pozostają w mm.

„Połącz litery mostkami” tworzy rzeczywistą geometrię pomiędzy najbliższymi fragmentami. „Połącz kropki i akcenty” robi to wewnątrz pojedynczego glifu. Wspólna płyta tylna jest pełnym prostokątem z tyłu, a nie dekoracją podglądu. Może istotnie zwiększyć masę i wymiary.

## Kaseton

Ścianka boczna jest offsetem obrysu do środka, nie skalowaniem litery. Tył, front i półka mają osobne grubości. Luz jest zawsze na stronę. Jeśli luz jest równy szerokości półki lub większy, projekt zostaje odrzucony. Kołnierz centruje front; nie zapewnia zatrzasku ani połączenia bez kleju.

Domyślna orientacja drukowania korpusu: tyłem na stole. Front drukuje się osobno płasko, np. z mlecznego PETG. Wartości 0,15–0,45 mm wymagają prób na swoim sprzęcie, nie gwarantują określonego pasowania.

## Edytor LED i montażu

1. Ustaw technologię, szerokość, wysokość i sposób mocowania. PCB wymaga także długości i liczby punktów.
2. „Zaproponuj rozmieszczenie” zastępuje sekcje LED nową propozycją, zachowując własne elementy montażowe. Ręczne pozycje LED zapisuj w JSON przed ponowną propozycją, jeśli chcesz je zachować.
3. Edytor 2D pokazuje obrys litery i komorę. Przeciągnij sekcję; po puszczeniu zostaje przeliczona geometria. W panelu wpisz dokładne X, Y i kąt. Zmiana wybranego elementu nie zmienia innych sekcji.
4. Dodaj otwory przewodów/śrub, keyhole, kieszenie, dystanse, kanały lub miejsca złączek. Mogą mieć inne wymiary niż źródło światła. Czerwone elementy nie mieszczą się w dostępnej geometrii.
5. Sprawdź kontrolę projektu. Podany „dostępny wymiar” jest lokalną średnicą wpisaną, a pełna kontrola używa obrysu elementu wraz z mocowaniami. Sama średnica nie jest gwarancją dopasowania obróconego prostokąta.

Mocowania są częścią korpusu, a LED i złączki to zakupione komponenty. Widok referencyjny nie jest zleceniem ich drukowania. Sprawdź rozstaw otworów rzeczywistej płytki; domyślne otwory podstawek mają Ø1,8 mm.

## Neon Flex

„Wyznacz linie środkowe” tworzy propozycję, często z kilkoma odcinkami i rozgałęzieniami. Nie oczekuj automatycznej pojedynczej taśmy w dowolnej literze. Wybierz trasę i przeciągnij węzły albo wpisz współrzędne. Możesz rysować własne trasy klikając w 2D; zakończ rysowanie przyciskiem w panelu.

„Zaokrąglij trasy” dodaje styczne łuki o wybranym promieniu. Nie mieści się? Rozsuń węzły albo zmień obrys/profile, bez zmniejszania promienia poniżej specyfikacji producenta. „Skróć do cięcia” usuwa część końca ścieżki, aby długość odpowiadała całkowitej liczbie sekcji.

Ostre zakręty, samoprzecięcia, kolizje rowków, brak materiału na ściankę i niedopasowanie cięcia blokują eksport. Łącz oddzielne sekcje przewodami po zaplanowaniu połączeń; aplikacja nie tworzy trasy przestrzennej z gięciem pionowym.

## Podgląd

LPM obraca, kółko przybliża, PPM przesuwa. Kamera ma widoki z góry XY, przodu, tyłu i boku. „Dopasuj kamerę” resetuje kadr. Wymiary wskazują rzeczywisty obrys złożenia.

Filtry: komplet, korpus, front, rozłożone części, przekrój, przezroczysty korpus, LED i układ części do druku. Rozłożenie przesuwa wyświetlane części bez zmiany współrzędnych montażowych w projekcie. Przekrój jest wyłącznie narzędziem oglądania — eksportuje się pełną bryłę. Symulacja światła nie jest obliczeniem fotometrycznym. Kolory w STL nie występują; 3MF zapisuje podstawowe materiały barwne, bez przypisania AMS.

Kliknij część pod modelem, aby ją zaznaczyć i pobrać wyłącznie jej STL. PNG zapisuje bieżący podgląd 3D. Przy braku WebGL można nadal korzystać z 2D i generować modele w Pythonie.

## Druk i segmentacja

Wybierz profil stołu albo wpisz własne XYZ. Ostrzeżenie stołu nie oznacza automatycznego podziału. Po włączeniu segmentów sprawdź gniazda i łączniki, dodatkowe 2 mm od tyłu, przebieg szwów i sposób wklejenia frontów. Podział przecinający mocowania lub z brakiem materiału na gniazda pozostaje błędem.

Najpierw pobierz i wydrukuj test luzów, potem mały fragment litery z mocowaniem. Sprawdź skurcz materiału, rzeczywistą grubość taśmy z komponentami i temperaturę pracy. Nie dobieraj zasilacza wyłącznie na podstawie W/m w tej aplikacji.

## Eksport i zapis

- ZIP: wszystkie części STL, ASSEMBLY.3mf, PRINT_LAYOUT.3mf, projekt i manifest. REFERENCYJNE złożenie LED ma nazwę DO_NOT_PRINT.
- 3MF: osobne obiekty w pozycjach montażowych; jeśli włączony jest widok „Układ do druku”, obiekty zostają rozłożone płasko.
- STL: części płasko na stole, bez materiałów. Przy eksporcie zbiorczym rozdziel obiekty w slicerze.
- JSON: wszystkie parametry i identyfikator fontu, do ponownego otwarcia. Zaimportuj ponownie ten sam font, jeśli brakuje go na innym komputerze.

„Zapisz projekt” zachowuje lokalny plik serwera i pobiera JSON. Lista ostatnich projektów jest lokalna dla instalacji. Szkic, motyw i presety są przechowywane w przeglądarce. Czyść je rozważnie — JSON jest przenośną kopią. Przyciski cofania/ponawiania zachowują do 60 zmian; nowy projekt i reset także można cofnąć. Ctrl+S pobiera JSON, Ctrl+Z/Ctrl+Shift+Z cofa/ponawia zmianę parametrów poza edycją pól tekstowych.
