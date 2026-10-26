#!/usr/bin/env python3
"""Prüft eine installierte (oder probeweise kopierte) Anwendung.

Aufruf::

    python3 -I pc/scripts/installation_pruefen.py /opt/stevie-empire/speichenrechner

Geladen wird ausschließlich aus dem angegebenen Ordner – nie aus dem Repo.
Geprüft wird, dass die Pfade dorthin zeigen, die Kataloge geladen werden und
die Rechnung für alle Fälle aus ``data/pruefwerte.json`` dieselben Zahlen
liefert wie in der Entwicklung: Länge, Bestelllänge, Dehnung, Ton, Gewicht.
Läuft ohne GTK; von ``test-install.sh`` und ``tests/test_paketierung.py``
benutzt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def pruefen(ziel: Path) -> list[str]:
    """Gibt die gefundenen Probleme zurück; leer heißt: alles in Ordnung."""
    sys.path.insert(0, str(ziel / "pc"))
    from speichenrechner import berechnung, felgenkunde, katalog, pfade
    from speichenrechner.modelle import Einspeichung, Felge, Nabe, Speichensatz

    probleme = []
    geladen = Path(pfade.__file__).resolve()
    if not geladen.is_relative_to(ziel.resolve()):
        probleme.append(f"Module kommen aus {geladen}, nicht aus {ziel}")
    if pfade.daten_verzeichnis() != ziel.resolve() / "data":
        probleme.append(f"Daten werden in {pfade.daten_verzeichnis()} gesucht")
    if not pfade.icon_pfad().is_file():
        probleme.append(f"Icon fehlt: {pfade.icon_pfad()}")
    if not katalog.lade().naben:
        probleme.append("Nabenkatalog leer")
    if not felgenkunde.lade().typen:
        probleme.append("Felgentypen leer")

    werte = json.loads((ziel / "data" / "pruefwerte.json").read_text(encoding="utf-8"))
    for fall in werte["faelle"]:
        e = fall["eingabe"]
        nabe = Nabe("p", e["flanschdurchmesser_links"], e["flanschdurchmesser_rechts"],
                    e["flanschabstand_links"], e["flanschabstand_rechts"],
                    e["speichenloch"], flanschdicke=e["flanschdicke"])
        felge = Felge("f", e["erd"], e["versatz"])
        einspeichung = Einspeichung(e["speichenzahl"], e["kreuzungen_links"],
                                    e["kreuzungen_rechts"], e["verteilung"])
        satz = Speichensatz(**e["speichen"]) if "speichen" in e else None
        ergebnis = berechnung.berechne(nabe, felge, einspeichung, e["schritt"], satz)
        for seite, s in (("links", ergebnis.links), ("rechts", ergebnis.rechts)):
            for feld, ist in (("laenge", s.laenge), ("bestell", s.laenge_gerundet),
                              ("dehnung", s.dehnung), ("frequenz", s.frequenz),
                              ("gewicht", s.gewicht)):
                soll = fall["erwartet"][f"{feld}_{seite}"]
                if round(ist, werte["stellen"]) != soll:
                    probleme.append(f"{fall['name']}: {feld}_{seite} {ist} statt {soll}")
    if not probleme:
        print(f"{len(werte['faelle'])} Prüffälle aus {ziel / 'data'} stimmen, "
              f"Kataloge geladen.")
    return probleme


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    probleme = pruefen(Path(sys.argv[1]))
    for problem in probleme:
        print(f"FEHLER: {problem}", file=sys.stderr)
    return 1 if probleme else 0


if __name__ == "__main__":
    sys.exit(main())
