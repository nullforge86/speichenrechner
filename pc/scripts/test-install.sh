#!/usr/bin/env bash
#
# Installiert das gebaute Paket probeweise, prüft es und entfernt es wieder.
#
#   pc/scripts/test-install.sh [pfad/zum/paket.deb]
#
# Ohne Angabe wird pc/dist/speichenrechner_<Fassung>_all.deb genommen.
#
# ACHTUNG: Das Skript ändert das System (apt install / apt purge, braucht
# sudo). Gedacht für eine Test-VM, einen Container oder die CI – nicht für den
# Rechner, auf dem der Speichenrechner im Alltag läuft. Eigene Einstellungen in
# ~/.config/speichenrechner/ fasst es nicht an.
#
set -Eeuo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC="$(cd "$DIR/.." && pwd)"
PAKET="speichenrechner"
ZIEL="/opt/stevie-empire/$PAKET"
STARTER="/usr/share/applications/stevie-$PAKET.desktop"
ICON="/usr/share/icons/hicolor/scalable/apps/de.speichenrechner.Speichenrechner.svg"

FASSUNG="$(sed -n 's/^VERSION = "\(.*\)"$/\1/p' "$PC/speichenrechner/__init__.py")"
DEB="$(realpath "${1:-$PC/dist/${PAKET}_${FASSUNG}_all.deb}")"

schritt() { printf '\n==> %s\n' "$*"; }
fehler() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }
trap 'fehler "abgebrochen in Zeile $LINENO: $BASH_COMMAND"' ERR

[ -f "$DEB" ] || fehler "$DEB fehlt – erst pc/scripts/build-deb.sh ausführen"

if [ "$(id -u)" -eq 0 ]; then SUDO=(); else SUDO=(sudo); fi
apt_() { "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get "$@"; }

pruefe_installation() {
    [ -d "$ZIEL/data" ]                          || fehler "$ZIEL/data fehlt"
    [ -f "$ZIEL/data/naben_katalog.json" ]       || fehler "Nabenkatalog fehlt"
    [ -x "$ZIEL/pc/speichenrechner.py" ]         || fehler "Startskript nicht ausführbar"
    [ -L "/usr/bin/$PAKET" ]                     || fehler "/usr/bin/$PAKET ist kein Symlink"
    [ "$(readlink -f "/usr/bin/$PAKET")" = "$ZIEL/pc/speichenrechner.py" ] ||
        fehler "/usr/bin/$PAKET zeigt auf $(readlink -f "/usr/bin/$PAKET")"
    [ -f "$STARTER" ]                            || fehler "$STARTER fehlt"
    grep -qx "Exec=/usr/bin/$PAKET" "$STARTER"   || fehler "Exec-Zeile im Starter falsch"
    [ -f "$ICON" ]                               || fehler "$ICON fehlt"
    dpkg -L "$PAKET" | grep -qx "$ZIEL/pc/speichenrechner.py" ||
        fehler "dpkg kennt $ZIEL/pc/speichenrechner.py nicht"
    echo "Pfade, Symlink, Starter und Icon in Ordnung."
}

selbsttest() {
    # Aus einem fremden Ordner und mit leerem Suchpfad starten: die Anwendung
    # darf weder das Arbeitsverzeichnis noch den Entwicklungsordner brauchen.
    local ausgabe
    # --pruefen endet ohne Bildschirm mit 1; ausgewertet wird der Bericht.
    ausgabe="$(cd / && { env -u PYTHONPATH -u DISPLAY -u WAYLAND_DISPLAY \
        "/usr/bin/$PAKET" --pruefen 2>&1 || true; })"
    echo "$ausgabe"
    grep -q "Speichenrechner $FASSUNG" <<<"$ausgabe" || fehler "falsche Fassung gemeldet"
    grep -q "Testrechnung .* in Ordnung" <<<"$ausgabe" || fehler "Testrechnung fehlgeschlagen"
    grep -q "Daten            $ZIEL/data" <<<"$ausgabe" ||
        fehler "Daten werden nicht aus $ZIEL/data geladen"
    if grep -q "FEHLT (" <<<"$ausgabe"; then
        echo "Hinweis: GTK fehlt auf diesem Rechner – Oberfläche nicht geprüft."
    fi
    if grep -E "^  [a-z_]+\.json +FEHLT" <<<"$ausgabe"; then
        fehler "Kataloge fehlen"
    fi
    # Dieselben Zahlen wie in der Entwicklung: alle Prüfwerte aus data/.
    (cd / && env -u PYTHONPATH python3 -I "$DIR/installation_pruefen.py" "$ZIEL")
}

schritt "Installieren: $DEB"
apt_ install -y "$DEB"
pruefe_installation
selbsttest

schritt "Entfernen"
apt_ purge -y "$PAKET"
for pfad in "$ZIEL" "/usr/bin/$PAKET" "$STARTER" "$ICON"; do
    if [ -e "$pfad" ] || [ -L "$pfad" ]; then
        fehler "$pfad nach dem Entfernen noch da"
    fi
done
[ ! -e /opt/stevie-empire ] || echo "Hinweis: /opt/stevie-empire bleibt (andere Pakete?)"
echo "Rückstandsfrei entfernt."

schritt "Erneut installieren"
apt_ install -y "$DEB"
pruefe_installation

schritt "Über sich selbst installieren (wie ein Update)"
# Bytecode, wie ihn ein Start als root hinterlässt – prerm muss ihn abräumen.
"${SUDO[@]}" python3 -c "import compileall,sys; compileall.compile_dir(sys.argv[1], quiet=1)" "$ZIEL/pc"
apt_ install -y --reinstall "$DEB"
pruefe_installation
apt_ purge -y "$PAKET"
[ ! -e "$ZIEL" ] || fehler "$ZIEL nach dem Entfernen noch da (Bytecode-Reste?)"

schritt "Alle Prüfungen bestanden"
