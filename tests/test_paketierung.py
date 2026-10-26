"""Prüft das Debian-Paket der PC-Fassung, ohne es zu bauen.

Gebaut und installiert wird mit ``pc/scripts/build-deb.sh`` und
``pc/scripts/test-install.sh`` (dazu braucht es debhelper und sudo). Hier
steht, was ohne beides geht: dass die Paketdateien zum Code passen und dass die
Anwendung im Aufbau unter ``/opt/stevie-empire/speichenrechner/`` dieselben
Zahlen liefert wie im Repo.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DEBIAN = WURZEL / "pc" / "packaging" / "debian"
SKRIPTE = WURZEL / "pc" / "scripts"
ZIEL = "opt/stevie-empire/speichenrechner"

sys.path.insert(0, str(WURZEL / "pc"))

from speichenrechner import VERSION  # noqa: E402


def _zeilen(name: str) -> list[list[str]]:
    text = (DEBIAN / name).read_text(encoding="utf-8")
    return [z.split() for z in text.splitlines() if z.strip() and not z.startswith("#")]


def _baue_nach(wurzel: Path) -> Path:
    """Legt an, was ``debian/install`` aus dem Repo ins Paket kopiert."""
    for quelle, ziel in _zeilen("install"):
        if quelle.startswith("debian/"):
            continue                  # entsteht erst beim Bauen
        dateien = sorted(WURZEL.glob(quelle))
        for datei in dateien:
            nach = wurzel / ziel / datei.name
            nach.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(datei, nach)
    return wurzel / ZIEL


class TestPaketdateien(unittest.TestCase):
    def test_fassung_im_changelog_passt_zum_code(self):
        kopf = (DEBIAN / "changelog").read_text(encoding="utf-8").splitlines()[0]
        self.assertRegex(kopf, rf"^speichenrechner \({re.escape(VERSION)}\) ")

    def test_paketname_und_abhaengigkeiten(self):
        control = (DEBIAN / "control").read_text(encoding="utf-8")
        self.assertIn("\nPackage: speichenrechner\n", control)
        self.assertIn("Architecture: all", control)
        depends = re.search(r"^Depends: (.*)$", control, re.M).group(1)
        for paket in ("python3", "python3-gi", "gir1.2-gtk-3.0"):
            with self.subTest(paket=paket):
                self.assertRegex(depends, rf"(^|, ){re.escape(paket)}( |,|$)")

    def test_jede_quelle_aus_install_gibt_es(self):
        for quelle, ziel in _zeilen("install"):
            with self.subTest(quelle=quelle):
                if quelle.startswith("debian/erzeugt/"):
                    self.assertIn(quelle, (DEBIAN / "rules").read_text(encoding="utf-8")
                                  .replace("$(APP_ID)", "de.speichenrechner.Speichenrechner"))
                else:
                    self.assertTrue(list(WURZEL.glob(quelle)), f"{quelle} trifft nichts")
                self.assertTrue(ziel.startswith((ZIEL + "/", "usr/share/")), ziel)

    def test_alle_module_kommen_mit(self):
        """Ein neuer Unterordner in pc/speichenrechner/ braucht eine Zeile in install."""
        quellen = {q for q, _ in _zeilen("install")}
        for ordner in (WURZEL / "pc" / "speichenrechner").rglob("*.py"):
            rel = ordner.parent.relative_to(WURZEL).as_posix() + "/*.py"
            with self.subTest(ordner=rel):
                self.assertIn(rel, quellen)

    def test_terminal_aufruf_zeigt_auf_das_startskript(self):
        (link,) = _zeilen("links")
        self.assertEqual(link, [f"{ZIEL}/pc/speichenrechner.py", "usr/bin/speichenrechner"])

    def test_starter_heisst_wie_vorgegeben_und_ruft_usr_bin(self):
        rules = (DEBIAN / "rules").read_text(encoding="utf-8")
        self.assertIn("s|@EXEC@|/usr/bin/speichenrechner|", rules)
        self.assertIn("stevie-speichenrechner.desktop", rules)
        vorlage = (WURZEL / "pc" / "data" / "de.speichenrechner.Speichenrechner.desktop.in")
        text = vorlage.read_text(encoding="utf-8")
        for zeile in ("Type=Application", "Name=Speichenrechner", "Exec=@EXEC@",
                      "Icon=@ICON@", "Terminal=false"):
            with self.subTest(zeile=zeile):
                self.assertIn(zeile + "\n", text)

    def test_skripte_sind_ausfuehrbar_und_streng(self):
        for name in ("build-deb.sh", "test-install.sh"):
            skript = SKRIPTE / name
            with self.subTest(skript=name):
                self.assertTrue(os.access(skript, os.X_OK), f"{name} nicht ausführbar")
                text = skript.read_text(encoding="utf-8")
                self.assertIn("set -Eeuo pipefail", text)
                self.assertIn('DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', text)
        self.assertTrue(os.access(DEBIAN / "rules", os.X_OK), "debian/rules nicht ausführbar")


class TestInstallierterAufbau(unittest.TestCase):
    """Die Anwendung im Aufbau von /opt – aus fremdem Ordner, ohne das Repo."""

    def test_gleiche_zahlen_wie_in_der_entwicklung(self):
        with tempfile.TemporaryDirectory() as ordner:
            # Mit Leerzeichen: Pfade dürfen nirgends zerlegt werden.
            wurzel = Path(ordner) / "System Wurzel"
            ziel = _baue_nach(wurzel)
            umgebung = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                        "HOME": ordner, "XDG_CONFIG_HOME": str(Path(ordner) / "config")}
            lauf = subprocess.run(
                [sys.executable, "-I", str(SKRIPTE / "installation_pruefen.py"), str(ziel)],
                cwd=ordner, env=umgebung, capture_output=True, text=True, check=False)
            self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
            self.assertIn("Prüffälle", lauf.stdout)

    def test_ohne_daten_meldet_pruefen_den_mangel(self):
        """Fehlt data/, sagt --pruefen wo gesucht wurde – statt still leer zu bleiben."""
        with tempfile.TemporaryDirectory() as ordner:
            ziel = _baue_nach(Path(ordner))
            shutil.rmtree(ziel / "data")
            lauf = subprocess.run(
                [sys.executable, "-I", str(ziel / "pc" / "speichenrechner.py"), "--pruefen"],
                cwd=ordner, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                                 "HOME": ordner},
                capture_output=True, text=True, check=False)
            self.assertNotEqual(lauf.returncode, 0)
            self.assertIn(f"Daten            {ziel.resolve() / 'data'}", lauf.stdout)
            self.assertRegex(lauf.stdout, r"naben_katalog\.json +FEHLT")


if __name__ == "__main__":
    unittest.main()
