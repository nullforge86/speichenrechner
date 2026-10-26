"""Kleine Bau-Helfer für eine ruhige, moderne GTK-Oberfläche."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

RAND = 14
ABSTAND = 10


def rahmen(
    titel: str,
    aktion: Gtk.Widget | None = None,
) -> Gtk.Frame:
    """Abschnitt mit zurückhaltender Überschrift statt klassischem Rahmen."""
    kasten = Gtk.Frame()
    kasten.set_shadow_type(Gtk.ShadowType.NONE)
    kasten.get_style_context().add_class("ui-abschnitt")

    beschriftung = Gtk.Label(label=titel, xalign=0.0)
    beschriftung.get_style_context().add_class("ui-abschnitt-titel")

    if aktion is None:
        kopf = beschriftung
    else:
        kopf = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        kopf.pack_start(beschriftung, False, False, 0)
        kopf.pack_start(aktion, False, False, 0)

    kasten.set_label_widget(kopf)
    kasten.set_label_align(0.0, 0.5)
    return kasten


def abschnitt(
    titel: str,
    aktion: Gtk.Widget | None = None,
) -> tuple[Gtk.Frame, Gtk.Grid]:
    """Moderater Abschnitt mit großzügigen Innenabständen."""
    rahmen_ = rahmen(titel, aktion)

    raster = Gtk.Grid(
        column_spacing=ABSTAND,
        row_spacing=8,
    )
    raster.set_border_width(RAND)
    rahmen_.add(raster)
    return rahmen_, raster


def zahlenfeld(
    minimum: float,
    maximum: float,
    schritt: float = 0.5,
    stellen: int = 1,
    wert: float = 0.0,
) -> Gtk.SpinButton:
    """Kompaktes Zahlenfeld mit systemabhängigem GTK-Theme."""
    feld = Gtk.SpinButton()
    feld.set_adjustment(
        Gtk.Adjustment(
            value=wert,
            lower=minimum,
            upper=maximum,
            step_increment=schritt,
            page_increment=schritt * 10,
        )
    )
    feld.set_digits(stellen)
    feld.set_numeric(True)
    feld.set_width_chars(6)
    feld.set_halign(Gtk.Align.START)
    feld.get_style_context().add_class("ui-zahlenfeld")
    return feld


def zeile(
    raster: Gtk.Grid,
    reihe: int,
    beschriftung: str,
    steuerelement: Gtk.Widget,
    einheit: str | None = "mm",
    hilfe: str | None = None,
) -> int:
    """Beschriftung, Eingabefeld und Einheit in einer Zeile."""
    label = Gtk.Label(label=beschriftung, xalign=0.0)
    label.set_halign(Gtk.Align.START)

    if hilfe:
        label.set_tooltip_text(hilfe)
        steuerelement.set_tooltip_text(hilfe)

    raster.attach(label, 0, reihe, 1, 1)
    raster.attach(steuerelement, 1, reihe, 1, 1)

    if einheit:
        einheit_label = Gtk.Label(label=einheit, xalign=0.0)
        einheit_label.get_style_context().add_class("dim-label")
        raster.attach(einheit_label, 2, reihe, 1, 1)

    return reihe + 1


def doppelzeile(
    raster: Gtk.Grid,
    reihe: int,
    beschriftung: str,
    links: Gtk.Widget,
    rechts: Gtk.Widget,
    einheit: str | None = "mm",
    hilfe: str | None = None,
) -> int:
    """Zwei vergleichbare Eingaben mit konsistenten Abständen."""
    label = Gtk.Label(label=beschriftung, xalign=0.0)
    label.set_halign(Gtk.Align.START)

    if hilfe:
        label.set_tooltip_text(hilfe)
        links.set_tooltip_text(hilfe)
        rechts.set_tooltip_text(hilfe)

    raster.attach(label, 0, reihe, 1, 1)

    felder = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=ABSTAND,
    )
    felder.pack_start(links, False, False, 0)
    felder.pack_start(rechts, False, False, 0)
    raster.attach(felder, 1, reihe, 1, 1)

    if einheit:
        einheit_label = Gtk.Label(label=einheit, xalign=0.0)
        einheit_label.get_style_context().add_class("dim-label")
        raster.attach(einheit_label, 2, reihe, 1, 1)

    return reihe + 1


def spaltenkoepfe(raster: Gtk.Grid, reihe: int) -> int:
    """Dezente Spaltenüberschriften für linke und rechte Bauteilseite."""
    kopf = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=ABSTAND,
    )

    for text in ("links", "rechts"):
        label = Gtk.Label(label=text, xalign=0.0)
        label.set_width_chars(7)
        label.get_style_context().add_class("dim-label")
        kopf.pack_start(label, False, False, 0)

    raster.attach(kopf, 1, reihe, 1, 1)
    return reihe + 1


def flachknopf(icon: str, tooltip: str) -> Gtk.Button:
    """Kleine, unaufdringliche Symbolschaltfläche."""
    schalter = Gtk.Button()
    schalter.set_relief(Gtk.ReliefStyle.NONE)
    schalter.set_focus_on_click(False)
    schalter.add(
        Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
    )
    schalter.set_tooltip_text(tooltip)
    return schalter


def knopf(
    beschriftung: str,
    icon: str | None = None,
    tooltip: str | None = None,
) -> Gtk.Button:
    """Schlichte Schaltfläche mit optionalem Symbol."""
    schalter = Gtk.Button()
    inhalt = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=6,
    )

    if icon:
        inhalt.pack_start(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON),
            False,
            False,
            0,
        )

    if beschriftung:
        inhalt.pack_start(
            Gtk.Label(label=beschriftung),
            False,
            False,
            0,
        )

    schalter.add(inhalt)

    if tooltip:
        schalter.set_tooltip_text(tooltip)

    return schalter
