"""Figs. 4-6 of the review: the S/phi dataset against phi, cover type, wind and gap size.

Fig. 4 (a) S against phi by cover group, with S = phi; (b) S/phi by cover group (measured conditions).
Fig. 5 S/phi against the wind speed at 2 m (measured conditions that report wind).
Fig. 6 S/phi against the gap length scale, with the band of Schlünder's gap model (Fig. 3) for
       close-packed discs and boundary layers of 1-10 mm.
Data: analise/dados_sintese.py (one report per experiment, S on the whole water surface).

    python -X utf8 fig04_06_sintese.py
"""
import math
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402
import dados_sintese  # noqa: E402
from fig03_regime_lacunas import s_sobre_phi, PHI_HEX  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

GRUPOS = [  # fixed categorical order of the style palette
    ("Floating elements", {"balls", "discs", "hexagons", "plates", "modular", "rafts", "granular"}),
    ("Suspended shade cloth", {"shade_cloth"}),
    ("PV panels (floating or above)", {"fpv"}),
    ("Continuous or perforated sheets", {"continuous_sheet", "perforated_sheet"}),
    ("Vegetation and other", {"vegetation", "other", "monolayer"}),
    ("Wind barriers (lattices)", set()),
]
LIM = (-1.0, 3.0)                       # S/phi axis; values outside are drawn on the edge and counted


def grupo(x):
    """Cover group of a condition; lattice wind barriers (cover class 'other') get their own group."""
    if x["cover_class"] == "other" and "lattice" in (x["condition"] + " " + x["notes"]).lower():
        return len(GRUPOS) - 1
    return next((i for i, (_, s) in enumerate(GRUPOS) if x["cover_class"] in s), len(GRUPOS) - 2)


def vento_2m(u, z):
    """Wind speed at 2 m from a speed at height z over water (log profile, z0 = 0.2 mm)."""
    if u is None:
        return None
    z = z if z and z > 0.05 else 2.0
    z0 = 2e-4
    return u * math.log(2 / z0) / math.log(z / z0)


def recorta(v):
    return float(np.clip(v, LIM[0] + 0.03, LIM[1] - 0.03))


def nota_recorte(ax, vals):
    n = sum(1 for v in vals if v < LIM[0] or v > LIM[1])
    if n:
        ax.text(0.99, 0.01, f"{n} value(s) beyond the axis drawn on its edge", transform=ax.transAxes,
                ha="right", va="bottom", color=estilo.INK2)


def marcas(g, modelo=False):
    """Colour and marker of a cover group (secondary encoding); model scenarios are hollow."""
    c = estilo.SERIES[g]
    if modelo:
        return dict(marker=estilo.MARKERS[g], facecolor="white", edgecolor=c, linewidth=0.8)
    return dict(marker=estilo.MARKERS[g], color=c, edgecolor="white", linewidth=0.4)


def legenda_grupos(fig, grupos, ncols, extra=()):
    h = [Line2D([], [], ls="none", marker=estilo.MARKERS[g], color=estilo.SERIES[g], markeredgecolor="white",
                markersize=5, label=GRUPOS[g][0]) for g in grupos]
    fig.legend(handles=h + list(extra), loc="outside lower center", ncols=ncols, handletextpad=0.3,
               columnspacing=1.2)


def main():
    d = [x for x in dados_sintese.carregar() if x["phi_n"] is not None and x["S_n"] is not None]
    med = [x for x in d if not x["modelo"]]
    estilo.setup()
    kw = dict(s=16, zorder=3)

    # Fig. 4
    fig, (a, b) = plt.subplots(1, 2, figsize=(estilo.WIDTH["full"], 92 * estilo.MM), layout="constrained",
                               gridspec_kw={"width_ratios": [1.15, 1]})
    a.plot([0, 1], [0, 1], color=estilo.MUTED, lw=0.8, ls="--")
    a.text(0.55, 0.60, "S = φ", color=estilo.INK2)
    for g, (nome, _) in enumerate(GRUPOS):
        for modelo in (False, True):
            pts = [(x["phi_n"], x["S_n"]) for x in d if grupo(x) == g and x["modelo"] == modelo]
            if pts:
                p, s = np.array(pts).T
                a.scatter(p, np.clip(s, -1.0, 1.02), **marcas(g, modelo), **kw)
    a.set_xlim(0, 1.02)
    a.set_ylim(-1.0, 1.05)
    a.set_xlabel("Covered fraction φ")
    a.set_ylabel("Suppression S = 1 − E_c/E_o")
    estilo.panel_label(a, "a")
    legenda_grupos(fig, sorted({grupo(x) for x in d}), 4, extra=[
        Line2D([], [], ls="none", marker="o", color=estilo.INK2, markeredgecolor="white", markersize=5,
               label="measured (filled)"),
        Line2D([], [], ls="none", marker="o", markerfacecolor="white", markeredgecolor=estilo.INK2,
               markersize=5, label="model scenario (hollow)")])
    rng = np.random.default_rng(1)
    vals, rotulos = [], []
    curto = ["Floating\nelements", "Shade\ncloth", "PV\npanels", "Sheets", "Vegetation,\nother", "Wind\nbarriers"]
    for g, (nome, _) in enumerate(GRUPOS):
        v = [x["S_over_phi_n"] for x in med if grupo(x) == g]
        vals += v
        n_est = len({x["grupo"] for x in med if grupo(x) == g})
        rotulos.append(f"{curto[g]}\n{len(v)} / {n_est}")
        if not v:
            continue
        xs = g + rng.uniform(-0.18, 0.18, len(v))
        b.scatter(xs, [recorta(u) for u in v], **marcas(g), **kw)
        mdn = float(np.median(v))
        if mdn > LIM[1]:
            b.text(g, LIM[1] - 0.18, f"median\n{mdn:.1f}", ha="center", va="top", color=estilo.INK)
        else:
            b.plot([g - 0.3, g + 0.3], [mdn, mdn], color=estilo.INK, lw=1.4, zorder=4)
    b.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
    b.set_xticks(range(len(GRUPOS)))
    b.set_xticklabels(rotulos)
    b.set_xlabel("conditions / studies", color=estilo.INK2)
    b.set_ylim(*LIM)
    b.set_ylabel("S/φ (measured; bar = median)")
    b.grid(axis="x", visible=False)
    nota_recorte(b, vals)
    estilo.panel_label(b, "b")
    estilo.save(fig, AQUI / "figuras" / "fig04_S_phi")

    # Fig. 5
    fig, ax = plt.subplots(figsize=(estilo.WIDTH["single"], 92 * estilo.MM), layout="constrained")
    ax.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
    pts = [(vento_2m(x["wind_n"], dados_sintese.num(x["wind_height_m"])), x["S_over_phi_n"], grupo(x))
           for x in med if x["wind_n"] is not None]
    for g, (nome, _) in enumerate(GRUPOS):
        q = [(u, v) for u, v, gg in pts if gg == g]
        if q:
            u, v = np.array(q).T
            ax.scatter(u, [recorta(t) for t in v], **marcas(g), **kw)
    ax.set_xlabel("Wind speed at 2 m (m s$^{-1}$)")
    ax.set_ylabel("S/φ (measured)")
    ax.set_ylim(*LIM)
    legenda_grupos(fig, sorted({gg for _, _, gg in pts}), 2)
    nota_recorte(ax, [v for _, v, _ in pts])
    estilo.save(fig, AQUI / "figuras" / "fig05_S_phi_vento")
    n5 = (len(pts), len({x["grupo"] for x in med if x["wind_n"] is not None}))

    # Fig. 6
    fig, ax = plt.subplots(figsize=(estilo.WIDTH["single"], 112 * estilo.MM), layout="constrained")
    gap = np.logspace(-4, 0, 200)                   # gap size (m); circular-gap radius r = gap/2
    lo = [s_sobre_phi(PHI_HEX, (g / 2) / 1e-2) for g in gap]
    hi = [s_sobre_phi(PHI_HEX, (g / 2) / 1e-3) for g in gap]
    banda = ax.fill_between(gap * 1000, lo, hi, color=estilo.SEQ[2], alpha=0.6, lw=0, zorder=1,
                            label="gap model, φ = 0.907, δ = 1–10 mm")
    ax.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
    pts = [(x["gap_n"], x["S_over_phi_n"], grupo(x)) for x in med if x["gap_n"]]
    for g, (nome, _) in enumerate(GRUPOS):
        q = [(u, v) for u, v, gg in pts if gg == g]
        if q:
            u, v = np.array(q).T
            ax.scatter(u * 1000, [recorta(t) for t in v], **marcas(g), **kw)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 1000)
    ax.set_ylim(*LIM)
    ax.set_xlabel("Gap length scale (mm)")
    ax.set_ylabel("S/φ (measured)")
    legenda_grupos(fig, sorted({gg for _, _, gg in pts}), 1, extra=[banda])
    nota_recorte(ax, [v for _, v, _ in pts])
    estilo.save(fig, AQUI / "figuras" / "fig06_S_phi_abertura")
    n6 = (len(pts), len({x["grupo"] for x in med if x["gap_n"]}))
    print(f"Fig 4: {len(d)} conditions ({len({x['grupo'] for x in d})} studies); "
          f"Fig 5: {n5[0]} conditions ({n5[1]} studies); Fig 6: {n6[0]} conditions ({n6[1]} studies)")


if __name__ == "__main__":
    main()
