"""Fig. 8 of the review: the transfer chain from laboratory S/phi to reservoirs (Section 10).

Four steps, left to right: laboratory basin, outdoor pan or tank, farm dam or pond, reservoir. Each column
gives the scale of the step (as in Section 10), a sketch (not to scale), the variables that govern S/phi
there with the quantity each one moves and its usual sign, and the evidence of the review at that step.
Chips in the colours of Fig. 2 mark the terms of the identity (r_open blue, r_under orange); grey chips
mark quantities outside the two terms (the reference E_o, the covered fraction or S itself changing in
time, the boundary-layer thickness delta).

Evidence is counted from the synthesis dataset (dados_sintese.carregar(), conditions with phi and S on
the whole surface), so it follows any update of the data:
- laboratory: measured studies run indoors (wind tunnel, or "lab"/"indoor" in the period or radiation
  fields), i.e. lamp-heated or unheated basins with fan wind or still air;
- pan or tank: the other measured laboratory-class studies (outdoor vessels), plus the field pond the size
  of a Class A pan;
- farm dam or pond: field studies on water bodies of 10 m2 or more;
- reservoir: no measured condition; model studies of water bodies of 1e5 m2 or more; the assumed-factor
  records of the search (numeros_sintese.json); the eddy-covariance study over a floating PV array on a
  reservoir that was available only as an abstract (Section 8, Berlioux et al. 2026), counted by hand.

    python -X utf8 fig08_transferencia.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402
from dados_sintese import carregar  # noqa: E402

import estilo_figuras as ef  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

W, H = 190.0, 156.0
C_OPEN, C_UNDER, C_OUTRO = estilo.SERIES[0], estilo.SERIES[1], ef.NEUTRAL
AGUA, AGUA2 = estilo.SEQ[0], estilo.SEQ[3]
ELEM = "#d6d4cc"
NCOL, GAP = 4, 4.6
CW = (W - 2.0 - (NCOL - 1) * GAP) / NCOL
XS = [1.0 + i * (CW + GAP) for i in range(NCOL)]
RO, RU = r"$r_\mathrm{open}$", r"$r_\mathrm{under}$"
Y_CAB, Y_ESB, Y_VAR, Y_EVI = 141.0, 117.0, 112.0, 4.0     # header, sketch, variables, evidence (bottoms/tops)
H_EVI = 36.0


# ------------------------------------------------------------------ evidence from the synthesis dataset
def evidencias():
    d = [x for x in carregar() if x["phi_n"] is not None and x["S_n"] is not None]
    area = lambda x: float(x["water_area_m2"]) if x["water_area_m2"] else None  # noqa: E731
    passo = defaultdict(lambda: defaultdict(list))
    for x in d:
        if x["classe_escala"] == "lab":
            txt = f'{x["season"]} {x["radiation"]}'
            interno = x["scale"] == "wind_tunnel" or re.search(r"\blab|indoor", txt, re.I)
            passo["lab" if interno else "pan"][x["grupo"]].append(x)
        elif x["classe_escala"] == "field":
            a = area(x)
            passo["dam" if a is not None and a >= 10 else "pan_campo"][x["grupo"]].append(x)
        elif x["classe_escala"] == "model":
            a = area(x)
            if a is not None and a >= 1e5:
                passo["res_model"][x["grupo"]].append(x)
    n = {k: (len(v), sum(len(r) for r in v.values())) for k, v in passo.items()}
    sp = [x["S_over_phi_n"] for v in passo["dam"].values() for x in v]
    num = json.loads((AQUI / "numeros_sintese.json").read_text(encoding="utf-8"))
    return n, (min(sp), max(sp)), num["search"]["assumed_factor"], passo


# ------------------------------------------------------------------ drawing helpers
def seta(ax, a, b, cor=None, lw=0.8, est="-|>", ms=6, **kw):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=est, mutation_scale=ms, color=cor or estilo.INK2, lw=lw,
                                 shrinkA=0, shrinkB=0, **kw))


def chip(ax, x, y, texto, cor):
    ax.text(x, y, texto, ha="left", va="center", color=estilo.INK, zorder=6,
            bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.5", fc=ef.tint(cor, 0.22), ec=cor, lw=0.6))


def caixa(ax, x, y, w, h, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=estilo.AXIS,
                                lw=0.7))


def flutuantes(ax, x0, x1, y, n, w=2.6, h=0.9):
    for xc in np.linspace(x0, x1, n):
        ax.add_patch(Rectangle((xc - w / 2, y - h / 2), w, h, fc=ELEM, ec=estilo.INK2, lw=0.4, zorder=4))


def esboco_lab(ax, x, y):
    # glass basin, lamp above, fan on the left
    bx, bw, bh = x + 12, 22, 7
    ax.add_patch(Rectangle((bx, y), bw, bh * 0.75, fc=AGUA, ec="none"))
    ax.plot([bx, bx, bx + bw, bx + bw], [y + bh, y, y, y + bh], color=estilo.INK2, lw=0.8)
    flutuantes(ax, bx + 2.5, bx + bw - 2.5, y + bh * 0.75, 6)
    ax.add_patch(Rectangle((bx + 4, y + 15.5), bw - 8, 1.6, fc="#f3c64b", ec=estilo.INK2, lw=0.5))
    for xl in np.linspace(bx + 6, bx + bw - 6, 4):
        ax.plot([xl, xl], [y + 15.0, y + 9.0], color="#c99a00", lw=0.6, ls=(0, (2, 1.2)))
    fx, fy = x + 5.5, y + 8.5
    ax.add_patch(plt.Circle((fx, fy), 3.0, fc="white", ec=estilo.INK2, lw=0.6))
    for ang in (0, 120, 240):
        t = np.radians(ang)
        ax.add_patch(Polygon([(fx, fy), (fx + 2.6 * np.cos(t + 0.35), fy + 2.6 * np.sin(t + 0.35)),
                              (fx + 2.6 * np.cos(t - 0.35), fy + 2.6 * np.sin(t - 0.35))], fc=estilo.MUTED, lw=0))
    ax.plot([fx, fx], [y, fy - 3.0], color=estilo.INK2, lw=0.6)
    seta(ax, (fx + 4.0, fy), (bx + 3.0, fy), lw=0.7, ms=4)


def esboco_pan(ax, x, y):
    # Class A pan on a wooden stand, sun and wind
    px, pw = x + 9, 24
    ax.add_patch(Rectangle((px, y + 3.0), pw, 3.6, fc=AGUA, ec="none"))
    ax.plot([px, px, px + pw, px + pw], [y + 7.6, y + 3.0, y + 3.0, y + 7.6], color=estilo.INK2, lw=0.8)
    flutuantes(ax, px + 2.5, px + pw - 2.5, y + 6.6, 5, w=3.4)
    for xs in np.linspace(px + 1, px + pw - 1, 5):
        ax.plot([xs, xs], [y, y + 3.0], color="#a07c4c", lw=1.2)
    ax.plot([px - 1, px + pw + 1], [y, y], color=estilo.INK2, lw=0.6)
    sx, sy = px + pw + 4.0, y + 15.0
    ax.add_patch(plt.Circle((sx, sy), 2.2, fc="#f3c64b", ec=estilo.INK2, lw=0.5))
    for ang in np.linspace(0, 2 * np.pi, 9)[:-1]:
        ax.plot([sx + 2.9 * np.cos(ang), sx + 3.8 * np.cos(ang)], [sy + 2.9 * np.sin(ang), sy + 3.8 * np.sin(ang)],
                color=estilo.INK2, lw=0.5)
    seta(ax, (x + 2.0, y + 12.0), (x + 12.0, y + 12.0), lw=0.7, ms=4)


def esboco_dam(ax, x, y):
    # earth embankment, waves, floats drifting and piling at the lee shore
    xs = np.linspace(x + 6, x + CW - 6, 200)
    sup = y + 9.0 + 0.55 * np.sin((xs - xs[0]) * 1.9)
    ax.add_patch(Polygon([(x + 3, y + 10.5), (x + 9, y + 1.0), (x + CW - 9, y + 1.0), (x + CW - 3, y + 10.5)],
                         fc="#e9e2d2", ec="none"))
    ax.fill_between(xs, y + 1.6, sup, where=(xs > x + 7) & (xs < x + CW - 7), color=AGUA, lw=0)
    ax.plot([x, x + 3, x + 9, x + CW - 9, x + CW - 3, x + CW], [y + 10.5, y + 10.5, y + 1.0, y + 1.0, y + 10.5,
                                                             y + 10.5], color=estilo.INK2, lw=0.8)
    ax.plot(xs[(xs > x + 7.5) & (xs < x + CW - 7.5)], sup[(xs > x + 7.5) & (xs < x + CW - 7.5)], color=C_OPEN,
            lw=0.7)
    for xc in (x + 16, x + 22, x + 27.5, x + 30.5, x + 33.5):
        yc = y + 9.0 + 0.55 * np.sin((xc - xs[0]) * 1.9)
        ax.add_patch(Rectangle((xc - 1.3, yc - 0.4), 2.6, 0.9, fc=ELEM, ec=estilo.INK2, lw=0.4, zorder=4))
    seta(ax, (x + 3.0, y + 15.0), (x + 15.0, y + 15.0), lw=0.7, ms=4)


def esboco_res(ax, x, y):
    # long water body with a floating array, fetch arrow and a thermocline
    ax.add_patch(Rectangle((x + 2, y + 1.0), CW - 4, 8.0, fc=AGUA, ec="none"))
    ax.add_patch(Rectangle((x + 2, y + 1.0), CW - 4, 3.6, fc=AGUA2, ec="none", alpha=0.6))
    ax.plot([x + 2, x + CW - 2], [y + 4.6, y + 4.6], color=estilo.INK2, lw=0.5, ls=(0, (3, 1.5)))
    ax.plot([x + 2, x + CW - 2], [y + 9.0, y + 9.0], color=C_OPEN, lw=0.8)
    for xc in np.linspace(x + 21, x + CW - 6, 5):
        ax.add_patch(Polygon([(xc - 1.8, y + 9.4), (xc + 1.6, y + 11.6), (xc + 2.1, y + 11.1), (xc - 1.3, y + 8.9)],
                             fc="#5d6f86", ec=estilo.INK2, lw=0.4, zorder=4))
    seta(ax, (x + 3.0, y + 18.0), (x + 19.0, y + 18.0), lw=0.7, ms=4)
    ax.annotate("", xy=(x + 3.0, y + 12.0), xytext=(x + 19.5, y + 12.0),
                arrowprops=dict(arrowstyle="<->", color=estilo.MUTED, lw=0.5, shrinkA=0, shrinkB=0))
    ax.text(x + 11.0, y + 12.6, "fetch", ha="center", va="bottom", color=estilo.INK2)


PASSOS = [
    ("Laboratory", "about 0.06–1.5 m²; fan wind,\nlamps or no radiation", esboco_lab, [
        (RO + " ↑", C_OPEN, "φ and gap regime r/δ"),
        (RO + " ±", C_OPEN, "energy balance of the\nelements (lamps or none)"),
        ("sets δ", C_OUTRO, "convection: Ra in still\nair, Ri in weak wind"),
    ]),
    ("Pan or tank outdoors", "about 0.005–5 m², most\nnear 1 m²; natural forcing", esboco_pan, [
        ("$E_o$", C_OUTRO, "sun, wind and humidity\nof the site"),
        ("$E_o$, $E_c$", C_OUTRO, "rim, walls and bird\nscreen act on both"),
        ("$E_o$", C_OUTRO, "pan rate is not a\nlake rate"),
    ]),
    ("Farm dam or pond", "10–10⁴ m², 1–5 m deep;\nwaves, weeks of storage", esboco_dam, [
        (RU + " ↑", C_UNDER, "waves wet the\nelements"),
        ("φ(t) ↓", C_OUTRO, "drift, blow-out and\nclustering of elements"),
        (RO + " ±", C_OPEN, "heat storage shifts\nthe saving in season"),
    ]),
    ("Reservoir", "10⁵ m² and larger; air\nadjusts over kilometres", esboco_res, [
        (RO + " ↑", C_OPEN, "fetch: humidified air,\nlower $E_o$ (gap covers)"),
        (RO + " ↓", C_OPEN, "array shelter and wake:\nlayout, wind rose"),
        (RO + " ?", C_OPEN, "r/δ set by array and\nwind; not measured"),
        (RO + " ±", C_OPEN, "stratification: mixed\nlayer sets $T_g$"),
        ("φ(t)", C_OUTRO, "level and area change\nthrough the year"),
        ("S(t) ↓", C_OUTRO, "ageing: wetting,\nfouling, wear"),
    ]),
]


def coluna(ax, i, nome, escala, esboco, variaveis):
    x = XS[i]
    caixa(ax, x, Y_CAB, CW, H - 1.0 - Y_CAB, fc=estilo.SEQ[0])
    ax.text(x + 2.0, H - 2.6, nome, ha="left", va="top", fontsize=9, fontweight="semibold", color=estilo.INK)
    ax.text(x + 2.0, H - 7.4, escala, ha="left", va="top", color=estilo.INK, linespacing=1.1)
    esboco(ax, x, Y_ESB + 2.0)
    y = Y_VAR - 3.0
    for rot, cor, texto in variaveis:
        chip(ax, x + 1.5, y, rot, cor)
        ax.text(x + 13.0, y, texto, ha="left", va="center", color=estilo.INK, linespacing=1.1)
        y -= 9.0


def evidencia(ax, n, faixa, assumidos):
    topo = Y_EVI + H_EVI
    ax.text(XS[0], topo + 2.0, "Evidence in the synthesis (studies with S and φ on the whole surface)",
            ha="left", va="bottom", fontsize=9, fontweight="semibold", color=estilo.INK)
    nmax = max(v[1] for v in n.values())
    linhas = [
        (n["lab"], ["measured indoors"]),
        (n["pan"], ["measured outdoors", f"+ {n['pan_campo'][0]} field pond of pan size"]),
        (n["dam"], ["measured in the field", f"S/φ {faixa[0]:.2f}–{faixa[1]:.2f}, all below 1"]),
        ((0, 0), [f"{n['res_model'][0]} model studies ({n['res_model'][1]} scenarios)",
                  "1 eddy-covariance study,", "abstract only, φ not stated",
                  f"{assumidos} records assume a factor"]),
    ]
    for i, ((ns, nc), txt) in enumerate(linhas):
        x = XS[i]
        caixa(ax, x, Y_EVI, CW, H_EVI)
        if i < 3:
            ax.text(x + 2.0, topo - 2.5, f"{ns} studies", ha="left", va="top", fontsize=11, fontweight="semibold",
                    color=estilo.INK)
            ax.text(x + 2.0, topo - 8.6, f"{nc} conditions", ha="left", va="top", color=estilo.INK)
        else:
            ax.text(x + 2.0, topo - 2.5, "no measurement", ha="left", va="top", fontsize=11, fontweight="semibold",
                    color=estilo.INK)
            ax.text(x + 2.0, topo - 8.6, "of S with φ in full text", ha="left", va="top", color=estilo.INK)
        # bar of measured conditions, on a common scale
        ax.add_patch(Rectangle((x + 2.0, topo - 14.6), CW - 4.0, 2.0, fc=estilo.GRID, ec="none"))
        if nc:
            ax.add_patch(Rectangle((x + 2.0, topo - 14.6), (CW - 4.0) * nc / nmax, 2.0, fc=estilo.SEQ[7], ec="none"))
        ax.text(x + 2.0, topo - 16.8, "\n".join(txt), ha="left", va="top", color=estilo.INK2, linespacing=1.15)


def main():
    n, faixa, assumidos, passo = evidencias()
    estilo.setup()
    fig = plt.figure(figsize=(W * estilo.MM, H * estilo.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    for i, p in enumerate(PASSOS):
        coluna(ax, i, *p)
        if i:
            xm = XS[i] - GAP / 2
            seta(ax, (xm - 1.8, Y_CAB + 7.0), (xm + 1.8, Y_CAB + 7.0), lw=1.2, ms=7)
    for i in range(1, NCOL):
        xm = XS[i] - GAP / 2
        ax.plot([xm, xm], [Y_EVI + H_EVI + 8.0, Y_CAB - 2.0], color=estilo.GRID, lw=0.8)
    evidencia(ax, n, faixa, assumidos)
    info = estilo.save(fig, AQUI / "figuras" / "fig08_transferencia")
    print(info["size_mm"], info["issues"])
    for k, (ns, nc) in sorted(n.items()):
        print(f"{k:10s} studies {ns:3d} conditions {nc:4d}: " + ", ".join(sorted(g[:24] for g in passo[k])))
    print(f"farm dam S/phi range {faixa[0]:.3f}-{faixa[1]:.3f}; assumed-factor records {assumidos}")


if __name__ == "__main__":
    main()
