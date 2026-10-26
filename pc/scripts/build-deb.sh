#!/usr/bin/env bash
#
# Baut das Debian-Paket der PC-Fassung.
#
#   pc/scripts/build-deb.sh              Tests, Paket bauen, Paket prüfen
#   pc/scripts/build-deb.sh --ohne-tests Tests überspringen (nur zum Ausprobieren)
#
# Benötigt (einmalig):  sudo apt install debhelper dpkg-dev
# Empfohlen:            sudo apt install lintian desktop-file-utils
#
# Das Ergebnis liegt in pc/dist/speichenrechner_<Fassung>_all.deb.
# Gebaut wird in einem Temp-Ordner – das Repo bleibt unverändert.
#
set -Eeuo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC="$(cd "$DIR/.." && pwd)"
WURZEL="$(cd "$PC/.." && pwd)"
DEBIAN="$PC/packaging/debian"
AUSGABE="$PC/dist"
PAKET="speichenrechner"
ZIEL="opt/stevie-empire/$PAKET"

TESTS=ja
case "${1:-}" in
    --ohne-tests) TESTS=nein ;;
    "") ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
esac

schritt() { printf '\n==> %s\n' "$*"; }
fehler() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }
trap 'fehler "abgebrochen in Zeile $LINENO: $BASH_COMMAND"' ERR

# 1./2. Wurzel, Werkzeuge und Eingabedateien prüfen ---------------------------
schritt "Projekt: $WURZEL"
for werkzeug in python3 dpkg-buildpackage dpkg-deb dh; do
    command -v "$werkzeug" >/dev/null 2>&1 ||
        fehler "$werkzeug fehlt – sudo apt install debhelper dpkg-dev python3"
done

# 3. Projektstruktur prüfen ---------------------------------------------------
for pfad in data/naben_katalog.json data/naben_zusatz.json \
            data/naben_modellreihen.json data/felgen_katalog.json \
            pc/speichenrechner.py pc/speichenrechner/__init__.py \
            pc/speichenrechner/pfade.py pc/data/speichenrechner.svg \
            pc/data/de.speichenrechner.Speichenrechner.desktop.in \
            pc/packaging/debian/control pc/packaging/debian/changelog; do
    [ -e "$WURZEL/$pfad" ] || fehler "$pfad fehlt"
done

# Die Fassung steht an genau einer Stelle im Code; changelog muss passen.
FASSUNG="$(sed -n 's/^VERSION = "\(.*\)"$/\1/p' "$PC/speichenrechner/__init__.py")"
[ -n "$FASSUNG" ] || fehler "VERSION in pc/speichenrechner/__init__.py nicht gefunden"
CHANGELOG="$(sed -n '1s/^[^ ]* (\([^)]*\)).*/\1/p' "$DEBIAN/changelog")"
[ "$FASSUNG" = "$CHANGELOG" ] ||
    fehler "Fassung $FASSUNG (Code) passt nicht zu $CHANGELOG (debian/changelog)"
echo "Fassung $FASSUNG"

# 4. Tests --------------------------------------------------------------------
if [ "$TESTS" = ja ]; then
    schritt "Tests"
    (cd "$WURZEL" && python3 -m unittest discover -s tests)
else
    schritt "Tests übersprungen (--ohne-tests)"
fi

# 5. Paket bauen --------------------------------------------------------------
schritt "Paket bauen"
ARBEIT="$(mktemp -d)"
trap 'rm -rf "$ARBEIT"' EXIT
QUELLE="$ARBEIT/$PAKET-$FASSUNG"
mkdir -p "$QUELLE/pc"
cp -a "$WURZEL/data" "$QUELLE/"
cp -a "$PC/speichenrechner.py" "$PC/speichenrechner" "$PC/data" "$QUELLE/pc/"
cp -a "$DEBIAN" "$QUELLE/debian"
find "$QUELLE" -name __pycache__ -type d -prune -exec rm -rf {} +
# Feste Zeitstempel aus dem changelog – gleicher Stand, gleiches Paket.
SOURCE_DATE_EPOCH="$(cd "$QUELLE" && dpkg-parsechangelog -STimestamp)"
export SOURCE_DATE_EPOCH
(cd "$QUELLE" && dpkg-buildpackage -us -uc -b)

DEB="$ARBEIT/${PAKET}_${FASSUNG}_all.deb"
[ -f "$DEB" ] || fehler "$DEB wurde nicht erzeugt"
mkdir -p "$AUSGABE"
cp "$DEB" "$AUSGABE/"
DEB="$AUSGABE/${PAKET}_${FASSUNG}_all.deb"

# 6./7. Metadaten prüfen ------------------------------------------------------
schritt "Metadaten"
feld() { dpkg-deb --field "$DEB" "$1"; }
[ "$(feld Package)" = "$PAKET" ]        || fehler "Package ist $(feld Package)"
[ "$(feld Version)" = "$FASSUNG" ]      || fehler "Version ist $(feld Version)"
[ "$(feld Architecture)" = all ]        || fehler "Architecture ist $(feld Architecture)"
for abh in python3 python3-gi gir1.2-gtk-3.0; do
    feld Depends | grep -qw -- "$abh" || fehler "Depends ohne $abh"
done
dpkg-deb --info "$DEB"

# 8. Installationspfade prüfen ------------------------------------------------
schritt "Inhalt"
INHALT="$(dpkg-deb --contents "$DEB")"
for pfad in "$ZIEL/pc/speichenrechner.py" \
            "$ZIEL/pc/speichenrechner/__main__.py" \
            "$ZIEL/pc/speichenrechner/pfade.py" \
            "$ZIEL/pc/speichenrechner/ui/hauptfenster.py" \
            "$ZIEL/pc/data/speichenrechner.svg" \
            "$ZIEL/data/naben_katalog.json" \
            "$ZIEL/data/felgen_katalog.json" \
            "usr/share/applications/stevie-$PAKET.desktop" \
            "usr/share/icons/hicolor/scalable/apps/de.speichenrechner.Speichenrechner.svg"; do
    grep -q " \./$pfad\$" <<<"$INHALT" || fehler "$pfad fehlt im Paket"
done
grep -q " \./usr/bin/$PAKET -> /$ZIEL/pc/speichenrechner.py\$" <<<"$INHALT" ||
    fehler "/usr/bin/$PAKET zeigt nicht auf /$ZIEL/pc/speichenrechner.py"
grep -q "^-rwxr-xr-x .* \./$ZIEL/pc/speichenrechner.py\$" <<<"$INHALT" ||
    fehler "$ZIEL/pc/speichenrechner.py ist nicht ausführbar"
# Nichts aus der Entwicklung darf mit: kein Bytecode, kein install.sh, keine Tests.
if grep -E '__pycache__|\.pyc$|install\.sh|/tests/|/packaging/' <<<"$INHALT"; then
    fehler "Paket enthält Entwicklungsdateien (siehe oben)"
fi
echo "$INHALT"

if command -v desktop-file-validate >/dev/null 2>&1; then
    schritt "Starter prüfen"
    dpkg-deb --fsys-tarfile "$DEB" |
        tar -xO "./usr/share/applications/stevie-$PAKET.desktop" > "$ARBEIT/starter.desktop"
    desktop-file-validate "$ARBEIT/starter.desktop"
    echo "stevie-$PAKET.desktop gültig"
else
    schritt "desktop-file-validate fehlt – Starter nicht geprüft"
fi

if command -v lintian >/dev/null 2>&1; then
    schritt "lintian"
    # Fehler brechen ab, Warnungen und Hinweise werden nur angezeigt.
    lintian --fail-on error --display-info "$DEB"
else
    schritt "lintian fehlt – Paket nicht gegen die Debian-Richtlinien geprüft"
fi

# 9. Ergebnis -----------------------------------------------------------------
schritt "Fertig"
echo "$DEB"
echo "Installieren:  sudo apt install $DEB"
