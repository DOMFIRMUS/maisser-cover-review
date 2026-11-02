"""Figure style of the review: the shared style of the articles (package estilo_figuras, in
`Artigos produzidos/_estilo_figuras`) under the names the figure scripts use.

Journal of Hydrology (Elsevier): 90 mm single column, 140 mm, 190 mm full width; lettering
8-12 pt. Each saved file is rescaled to the exact column width it was drawn for. Articles 1
and 2 keep their own style (`_comum/tanque/estilo.py`, archived in the v1.0.0 deposit).
"""
from pathlib import Path

import estilo_figuras as ef

SERIES = ef.COLORS
MARKERS = ef.MARKERS
SEQ = ef.BLUES
INK, INK2, MUTED, GRID, SURFACE = ef.INK, ef.INK2, ef.MUTED, ef.GRID, ef.SURFACE
AXIS = "#c3c2b7"
RING = ef.RING
MM = ef.MM
WIDTH = {"single": ef.width_in("elsevier-1"), "onehalf": ef.width_in("elsevier-1.5"),
         "full": ef.width_in("elsevier-2")}
JOURNAL = ("elsevier-1", "elsevier-1.5", "elsevier-2")


def setup():
    ef.use()


def panel_label(ax, s, **kw):
    ef.panel_labels(ax, start=s, **kw)


def save(fig, path, png=True):
    w = fig.get_size_inches()[0] / MM
    journal = min(JOURNAL, key=lambda k: abs(ef.WIDTHS_MM[k] - w))
    return ef.save(fig, Path(path), ("pdf", "png") if png else ("pdf",), journal=journal)
