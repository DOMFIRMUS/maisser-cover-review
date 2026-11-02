"""Fig. 4 of the review (preliminary while the extraction is incomplete): S against phi by scale.

Reads dados_S_phi/S_phi.csv and keeps the conditions of the studies in the synthesis (decision
include or include_model) whose S refers to the whole water surface and has a phi. Reports of
the same experiment are not merged yet. (a) S against phi with the area-proportional line;
(b) S/phi against phi.

    python -X utf8 fig04_S_phi.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

GRUPOS = [  # (label, scales), in the fixed categorical order of the style
    ("Pans, tanks and wind tunnels", {"pan", "tank", "wind_tunnel", "other"}),
    ("Ponds, reservoirs and lakes", {"pond", "dam", "reservoir", "lake"}),
    ("Model scenarios", {"model_only"}),
]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def dados():
    out = []
    for r in csv.DictReader(open(RAIZ / "dados_S_phi" / "S_phi.csv", encoding="utf-8-sig")):
        phi, s = num(r["phi"]), num(r["S"])
        if r["decision"] in ("include", "include_model") and r["S_basis"] == "total_surface" \
                and phi is not None and s is not None and phi > 0:
            modelo = r["model_based"] == "True" or r["decision"] == "include_model" or r["scale"] == "model_only"
            g = 2 if modelo else next((i for i, (_, esc) in enumerate(GRUPOS[:2]) if r["scale"] in esc), 0)
            out.append((g, phi, s, r["study"]))
    return out


def main():
    d = dados()
    estilo.setup()
    fig, (a, b) = plt.subplots(1, 2, figsize=(estilo.WIDTH["full"], 84 * estilo.MM), layout="constrained")
    x = np.linspace(0, 1, 2)
    a.plot(x, x, color=estilo.MUTED, lw=0.8, ls="--")
    a.text(0.62, 0.66, "S = φ", color=estilo.INK2, rotation=0)
    b.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
    for g, (rotulo, _) in enumerate(GRUPOS):
        pts = [(p, s) for gg, p, s, _ in d if gg == g]
        if not pts:
            continue
        p, s = np.array(pts).T
        n_est = len({st for gg, _, _, st in d if gg == g})
        kw = dict(s=16, color=estilo.SERIES[g], marker=estilo.MARKERS[g], edgecolor="white", linewidth=0.5,
                  alpha=0.9, zorder=3,
                  label=f"{rotulo} ({len(pts)} conditions, {n_est} {'study' if n_est == 1 else 'studies'})")
        a.scatter(p, s, **kw)
        b.scatter(p, np.clip(s / p, -1.5, 4.5), **{**kw, "label": None})
    a.set_xlim(0, 1.02)
    a.set_ylim(-1.0, 1.02)
    a.set_xlabel("Covered fraction φ")
    a.set_ylabel("Suppression S = 1 − E_c/E_o")
    fig.legend(*a.get_legend_handles_labels(), loc="outside lower center", ncols=2, handletextpad=0.3)
    estilo.panel_label(a, "a")
    b.set_xlim(0, 1.02)
    b.set_ylim(-1.6, 4.6)
    b.set_xlabel("Covered fraction φ")
    b.set_ylabel("Suppression per unit cover, S/φ")
    estilo.panel_label(b, "b")
    estilo.save(fig, AQUI / "figuras" / "fig04_S_phi_preliminar")
    print(f"{len(d)} conditions from {len({x[3] for x in d})} studies plotted")


if __name__ == "__main__":
    main()
