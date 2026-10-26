"""Alle Ablageorte an einer Stelle – mitgelieferte Dateien und XDG-Ordner.

Die mitgelieferten Dateien werden immer vom Ort dieses Moduls aus gesucht,
nie vom Arbeitsverzeichnis aus. Das Debian-Paket legt unter
``/opt/stevie-empire/speichenrechner/`` denselben Aufbau an wie das Repo
(``data/`` neben ``pc/``) – deshalb gilt dieselbe Rechnung im
Entwicklungsordner und in der Installation.
"""

from __future__ import annotations

import os
from pathlib import Path

ORDNERNAME = "speichenrechner"


def konfig_verzeichnis() -> Path:
    """``$XDG_CONFIG_HOME/speichenrechner`` bzw. ``~/.config/speichenrechner``."""
    basis = os.environ.get("XDG_CONFIG_HOME")
    wurzel = Path(basis) if basis else Path.home() / ".config"
    return wurzel / ORDNERNAME


def projekt_verzeichnis() -> Path:
    """Wurzel des Projekts – darin liegen ``pc/``, ``app/`` und ``data/``.

    ``data/`` enthält, was **beide** Fassungen brauchen: die Kataloge und die
    Prüfwerte. Es liegt deshalb nicht in einer der beiden, sondern daneben.
    """
    return Path(__file__).resolve().parents[2]


def daten_verzeichnis() -> Path:
    """Die geteilten Kataloge und Prüfwerte – ``data/`` in der Projektwurzel."""
    return projekt_verzeichnis() / "data"


def pc_verzeichnis() -> Path:
    """Ordner der PC-Fassung – darin liegt, was nur sie betrifft."""
    return Path(__file__).resolve().parents[1]


def icon_pfad() -> Path:
    """Anwendungs-Icon – gehört zur PC-Fassung, nicht zu den geteilten Daten."""
    return pc_verzeichnis() / "data" / "speichenrechner.svg"
