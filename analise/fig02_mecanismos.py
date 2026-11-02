"""Fig. 2 of the review: the three mechanisms that make S differ from phi, on one partly covered surface.

Schematic, no data. One cross-section of floating elements on water, in three zones:
(1) gap evaporation under the diffusive boundary layer of thickness delta (vapour shells of narrow gaps
merge below delta; the concentration layer restarts at the upwind edge of each gap in wind; Section 5);
(2) energy and thermal feedback of the elements (shading, heat absorbed by the elements going mostly to
the air and partly to the water, warm gap water T_g; Section 6); (3) aerodynamic sheltering (slower air
and a thicker delta among elements that stand above the water; Section 7). Below, the identity of the
review (Eq. identity, Section 3),

    S/phi - 1 = [(1 - phi)/phi] (1 - r_open) - r_under,

and, under each zone, the term that mechanism acts through and its usual sign. In the cross-section the
open water surface is drawn in the colour of r_open and the water beneath the elements in that of r_under.

    python -X utf8 fig02_mecanismos.py
"""
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402

import estilo_figuras as ef  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

W, H = 190.0, 112.0                       # drawing in mm (1 data unit = 1 mm)
C_OPEN, C_UNDER = estilo.SERIES[0], estilo.SERIES[1]     # r_open (blue), r_under (orange)
T_OPEN, T_UNDER = ef.tint(C_OPEN, 0.25), ef.tint(C_UNDER, 0.25)
AGUA, AGUA2 = estilo.SEQ[0], estilo.SEQ[2]
ELEM, ELEM_ESC = "#d6d4cc", "#3c3b38"     # light and dark (absorbing) elements
Y_SUP, Y_FUNDO = 70.0, 55.0               # water surface and bottom of the drawn water
ZONAS = [(5.0, 63.0), (67.0, 123.0), (127.0, 185.0)]
RO, RU = r"$r_\mathrm{open}$", r"$r_\mathrm{under}$"


def seta(ax, a, b, cor=None, lw=0.8, estilo_seta="-|>", ms=6, **kw):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo_seta, mutation_scale=ms, color=cor or estilo.INK2,
                                 lw=lw, shrinkA=0, shrinkB=0, **kw))


def elemento(ax, x0, x1, cor=ELEM, alto=2.6, imerso=1.2):
    """Floating flat element: top at Y_SUP + alto - imerso, bottom at Y_SUP - imerso; water beneath in C_UNDER."""
    ax.add_patch(FancyBboxPatch((x0, Y_SUP - imerso), x1 - x0, alto, boxstyle="round,pad=0,rounding_size=0.6",
                                fc=cor, ec=estilo.INK2, lw=0.5, zorder=4))
    ax.plot([x0 + 0.3, x1 - 0.3], [Y_SUP - imerso - 0.55] * 2, color=C_UNDER, lw=1.6,
            solid_capstyle="butt", zorder=5)


def superficie_aberta(ax, x0, x1):
    ax.plot([x0, x1], [Y_SUP, Y_SUP], color=C_OPEN, lw=1.6, solid_capstyle="butt", zorder=3)


def titulo(ax, z, n, texto):
    x0, x1 = ZONAS[z]
    ax.text(x0, H - 1, n, ha="left", va="top", fontsize=9.5, fontweight="bold", color=estilo.INK)
    ax.text(x0 + 4.2, H - 1, texto, ha="left", va="top", fontsize=9, fontweight="semibold", color=estilo.INK)


def chip(ax, x, y, texto, cor, ha="left"):
    return ax.text(x, y, texto, ha=ha, va="center", color=estilo.INK, zorder=6,
                   bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.5", fc=ef.tint(cor, 0.22), ec=cor, lw=0.6))


def zona_lacunas(ax):
    x0, x1 = ZONAS[0]
    blocos = [(x0 + 1, 17.0), (19.0, 31.0), (33.0, 45.0), (54.0, x1 - 1)]     # narrow gaps of 2 mm, one wide gap
    for a, b in blocos:
        elemento(ax, a, b)
    for a, b in zip([x0] + [b for _, b in blocos], [a for a, _ in blocos] + [x1]):
        if b - a > 0.2:
            superficie_aberta(ax, a, b)
    delta = Y_SUP + 9.0
    ax.plot([x0, 45.5], [delta, delta], color=estilo.INK2, lw=0.7, ls=(0, (4, 2)))
    ax.text(x0 + 0.5, delta + 0.8, "δ", ha="left", va="bottom", fontsize=9, color=estilo.INK)
    seta(ax, (x0 + 4.5, Y_SUP + 1.6), (x0 + 4.5, delta), estilo_seta="<|-|>", ms=4, lw=0.5)
    # vapour shells over the narrow gaps: they merge into flat contours below delta
    t = np.linspace(0, np.pi, 60)
    for xc in (18.0, 32.0):
        for r in (2.2, 4.2, 6.4):
            ax.plot(xc + r * np.cos(t), Y_SUP + 1.4 + 0.95 * r * np.sin(t), color=C_OPEN, lw=0.6, alpha=0.9,
                    zorder=2)
    ax.plot([x0, 45.5], [Y_SUP + 8.0] * 2, color=C_OPEN, lw=0.6, alpha=0.9)
    # wide gap in wind: the concentration layer restarts at the upwind edge
    seta(ax, (47.0, 84.0), (61.0, 84.0), lw=0.9)
    ax.text(47.0, 85.2, "wind", ha="left", va="bottom", color=estilo.INK2)
    xs = np.linspace(45.0, 54.0, 40)
    ax.fill_between(xs, Y_SUP, Y_SUP + 1.25 * np.sqrt(xs - 45.0), color=T_OPEN, lw=0, zorder=1)
    ax.plot(xs, Y_SUP + 1.25 * np.sqrt(xs - 45.0), color=C_OPEN, lw=0.8)
    # labels
    ax.text(x0 + 1, 105.0, "Gaps narrower than δ: vapour\nshells merge below δ, so the\nflux per open area rises",
            ha="left", va="top", color=estilo.INK, linespacing=1.15)
    ax.annotate("Edge: the vapour layer restarts\nat each gap in wind", xy=(50.0, Y_SUP + 1.2),
                xytext=(x1 - 1.0, Y_FUNDO + 6.0), ha="right", va="center", color=estilo.INK, linespacing=1.1,
                arrowprops=dict(arrowstyle="-", color=estilo.MUTED, lw=0.5, shrinkA=0, shrinkB=1))


def zona_energia(ax):
    x0, x1 = ZONAS[1]
    blocos = [(x0 + 1, 87.0), (91.0, 108.0), (112.0, x1 - 1)]
    for a, b in blocos:
        elemento(ax, a, b, cor=ELEM_ESC)
    for a, b in zip([x0] + [b for _, b in blocos], [a for a, _ in blocos] + [x1]):
        if b - a > 0.2:
            superficie_aberta(ax, a, b)
    # sun and rays
    sx, sy, rs = x0 + 4.5, 99.0, 2.6
    ax.add_patch(plt.Circle((sx, sy), rs, fc="#f3c64b", ec=estilo.INK2, lw=0.5, zorder=4))
    for ang in np.linspace(0, 2 * np.pi, 9)[:-1]:
        ax.plot([sx + 1.35 * rs * np.cos(ang), sx + 1.8 * rs * np.cos(ang)],
                [sy + 1.35 * rs * np.sin(ang), sy + 1.8 * rs * np.sin(ang)], color=estilo.INK2, lw=0.5)
    for xa in (78.0, 89.0, 99.0):           # rays leave the sun and reach the elements and the gap
        v = np.array([xa - sx, Y_SUP + 1.6 - sy])
        a = np.array([sx, sy]) + 2.1 * rs * v / np.hypot(*v)
        seta(ax, tuple(a), (xa, Y_SUP + 1.6), cor="#c99a00", lw=0.7, ms=5)
    # shaded, cooler water beneath the first element; warm gap water
    ax.add_patch(Polygon([(x0 + 1, Y_SUP - 1.9), (87.0, Y_SUP - 1.9), (88.0, Y_FUNDO + 2.0), (x0 + 1, Y_FUNDO + 2.0)],
                         closed=True, fc=AGUA2, ec="none", alpha=0.75, zorder=1))
    ax.text(x0 + 2.0, Y_FUNDO + 6.5, "shaded,\ncooler", ha="left", va="center", color=estilo.INK, linespacing=1.1,
            zorder=3)
    # heat of the middle element: most to the air, part to the water
    xm = 103.0
    seta(ax, (xm - 2.0, Y_SUP + 1.8), (xm - 2.0, 82.5), cor=C_UNDER, lw=1.0, connectionstyle="arc3,rad=-0.15")
    seta(ax, (xm + 2.0, Y_SUP + 1.8), (xm + 2.0, 82.5), cor=C_UNDER, lw=1.0, connectionstyle="arc3,rad=0.15")
    ax.text(xm + 4.5, 80.5, "heat to\nair (most)", ha="left", va="center", color=estilo.INK, linespacing=1.1)
    seta(ax, (xm + 4.0, Y_SUP - 2.2), (xm + 4.0, Y_SUP - 7.5), cor=C_UNDER, lw=0.8)
    ax.text(xm + 5.5, Y_SUP - 5.3, "to water", ha="left", va="center", color=estilo.INK)
    ax.annotate("warm gap\nwater, $T_g$", xy=(89.0, Y_SUP - 0.3), xytext=(96.5, Y_FUNDO + 6.5), ha="center",
                va="center", color=estilo.INK, linespacing=1.1,
                arrowprops=dict(arrowstyle="-", color=estilo.MUTED, lw=0.5, shrinkA=1, shrinkB=0))
    ax.text(x0 + 13.0, 105.0, "Elements absorb sunlight\nand shade the water\nbeneath them",
            ha="left", va="top", color=estilo.INK, linespacing=1.15)


def zona_abrigo(ax):
    x0, x1 = ZONAS[2]
    # floats carrying tilted panels (elements standing above the water)
    pos = [144.0, 159.0, 174.0]
    abertos = [(x0, pos[0] - 3.5)]
    for i, p in enumerate(pos):
        elemento(ax, p - 3.5, p + 3.5)
        ax.add_patch(Polygon([(p - 5.5, Y_SUP + 3.0), (p + 5.0, Y_SUP + 9.5), (p + 5.6, Y_SUP + 8.8),
                              (p - 4.9, Y_SUP + 2.3)], closed=True, fc="#5d6f86", ec=estilo.INK2, lw=0.5, zorder=4))
        ax.plot([p, p], [Y_SUP + 1.4, Y_SUP + 5.6], color=estilo.INK2, lw=0.8, zorder=3)
        fim = pos[i + 1] - 3.5 if i + 1 < len(pos) else x1
        abertos.append((p + 3.5, fim))
    for a, b in abertos:
        superficie_aberta(ax, a, b)
    # wind profile upstream (log-like) and weak flow in the lee of the panels
    zs = np.array([72.6, 76.8, 81.0, 86.0, 92.0])
    us = 2.2 * np.log((zs - Y_SUP) / 0.6)
    for z, u in zip(zs, us):
        seta(ax, (x0 + 0.5, z), (x0 + 0.5 + u, z), lw=0.8, ms=5)
    ax.plot([x0 + 0.5, x0 + 0.5], [Y_SUP + 1.0, 93.5], color=estilo.INK2, lw=0.5)
    ax.text(x0 + 1.0, 94.0, "wind", ha="left", va="bottom", color=estilo.INK2)
    for xg in (151.5, 166.5, 181.5):
        seta(ax, (xg - 1.5, Y_SUP + 1.6), (xg + 0.6, Y_SUP + 1.6), lw=0.6, ms=4)
    # boundary layer thickening over the array (drawn downwind of the profile, clear of the panels)
    xs = np.array([x0 + 9.0, 145.5, x1])
    ys = np.array([Y_SUP + 3.4, Y_SUP + 12.5, Y_SUP + 13.5])
    ax.plot(xs, ys, color=estilo.INK2, lw=0.7, ls=(0, (4, 2)))
    ax.text(x1, Y_SUP + 14.2, "δ", ha="right", va="bottom", fontsize=9, color=estilo.INK)
    ax.text(x0 + 13.0, 105.0, "Elements standing above the\nwater slow the air over the gaps;\nδ thickens downwind",
            ha="left", va="top", color=estilo.INK, linespacing=1.15)


def agua(ax):
    for x0, x1 in ZONAS:
        ax.add_patch(Rectangle((x0, Y_FUNDO), x1 - x0, Y_SUP - Y_FUNDO, fc=AGUA, ec="none", zorder=0))
    for x in (65.0, 125.0):
        ax.plot([x, x], [Y_FUNDO, H - 1], color=estilo.GRID, lw=0.8)


def identidade(ax):
    """The identity written in pieces, so the two terms can be underlined in their colours."""
    y = 45.0
    pecas = [(r"$\dfrac{S}{\mathrm{φ}} - 1 \;=\; \dfrac{1-\mathrm{φ}}{\mathrm{φ}}\,$", None),
             (r"$\left(1 - r_\mathrm{open}\right)$", C_OPEN),
             (r"$\;-\;$", None),
             (r"$r_\mathrm{under}$", C_UNDER)]
    fig = ax.figure
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    textos, larg = [], []
    for s, _ in pecas:
        t = ax.text(0, y, s, ha="left", va="center", fontsize=11, color=estilo.INK)
        bb = t.get_window_extent(rend)
        (a, _), (b, _) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        textos.append(t)
        larg.append(b - a)
    x = W / 2 - sum(larg) / 2
    caixas = []
    for t, w in zip(textos, larg):
        t.set_x(x)
        caixas.append((x, x + w))
        x += w
    for (a, b), (_, cor) in zip(caixas, pecas):
        if cor:
            ax.plot([a + 0.6, b - 0.6], [y - 5.2] * 2, color=cor, lw=2.0, solid_capstyle="butt")
    a, b = caixas[1]
    ax.text(b - 0.6, y - 6.8, "open water", ha="right", va="top", color=estilo.INK)
    a, b = caixas[3]
    ax.text(a + 0.6, y - 6.8, "covered area", ha="left", va="top", color=estilo.INK)
    # key to the colours of the cross-section
    kx, ky = 147.0, y + 2.8
    ax.plot([kx, kx + 6], [ky, ky], color=C_OPEN, lw=1.6, solid_capstyle="butt")
    ax.text(kx + 7.5, ky, "open water, rate " + RO + r"$\,E_o$", ha="left", va="center", color=estilo.INK)
    ax.plot([kx, kx + 6], [ky - 5.0, ky - 5.0], color=C_UNDER, lw=1.6, solid_capstyle="butt")
    ax.text(kx + 7.5, ky - 5.0, "under the cover, " + RU + r"$\,E_o$", ha="left", va="center", color=estilo.INK)


def efeitos(ax):
    """What each mechanism does to the terms of the identity (bottom row, aligned with the zones)."""
    y0 = 2.0
    for x0, x1 in ZONAS:
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, 27.0, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="white", ec=estilo.AXIS, lw=0.7))
    ax.text(5.0, 31.5, "Term moved and usual sign", ha="left", va="bottom", fontsize=9, fontweight="semibold",
            color=estilo.INK)
    x0 = ZONAS[0][0] + 2.0
    chip(ax, x0, 24.0, RO + r"$\,>1$", C_OPEN)
    ax.text(x0 + 16.5, 24.0, "so S/φ < 1", ha="left", va="center", color=estilo.INK)
    ax.text(x0, 16.0, "The excess grows as r/δ falls below\nabout 3; none for gaps much wider than δ",
            ha="left", va="center",
            color=estilo.INK, linespacing=1.15)
    ax.text(x0, 7.0, "Edges add to it in wind", ha="left", va="center", color=estilo.INK)
    x0 = ZONAS[1][0] + 2.0
    chip(ax, x0, 24.0, RO + r"$\,<1$", C_OPEN)
    ax.text(x0 + 16.5, 24.0, "shading cools the gaps", ha="left", va="center", color=estilo.INK)
    chip(ax, x0, 15.5, RO + r"$\,>1$", C_OPEN)
    ax.text(x0 + 16.5, 15.5, "heat from elements,\ninsulation, storage", ha="left", va="center", color=estilo.INK,
            linespacing=1.1)
    chip(ax, x0, 6.5, RU + r"$\,>0$", C_UNDER)
    ax.text(x0 + 16.5, 6.5, "heat and vapour through\nporous or translucent covers", ha="left", va="center",
            color=estilo.INK, linespacing=1.1)
    x0 = ZONAS[2][0] + 2.0
    chip(ax, x0, 24.0, RO + r"$\,<1$", C_OPEN)
    ax.text(x0 + 16.5, 24.0, "S/φ can exceed 1", ha="left", va="center", color=estilo.INK)
    ax.text(x0, 16.0, "Forced convection only: no\neffect in calm air", ha="left", va="center", color=estilo.INK,
            linespacing=1.15)
    ax.text(x0, 7.0, "Under suspended covers, also lowers " + RU, ha="left", va="center", color=estilo.INK)


def main():
    estilo.setup()
    fig = plt.figure(figsize=(W * estilo.MM, H * estilo.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    titulo(ax, 0, "1", "Gap evaporation")
    titulo(ax, 1, "2", "Energy and thermal feedback")
    titulo(ax, 2, "3", "Aerodynamic sheltering")
    agua(ax)
    zona_lacunas(ax)
    zona_energia(ax)
    zona_abrigo(ax)
    identidade(ax)
    efeitos(ax)
    info = estilo.save(fig, AQUI / "figuras" / "fig02_mecanismos")
    print(info["size_mm"], info["issues"])


if __name__ == "__main__":
    main()
