"""Fig. 7 of the review: floating photovoltaics - measured, modelled and assumed reduction per unit cover.

Measured and modelled S/phi of PV covers come from the synthesis (dados_sintese.py, cover class fpv).
Assumed factors come from the assumed-factor studies (dados_S_phi/fatores_supostos.json, extracted from
their abstracts): a factor applied to the area under the array is already a reduction per unit cover;
a factor for the whole water surface is divided by phi when phi is given, otherwise left out (counted
in the caption note).

    python -X utf8 fig07_fpv.py
"""
import json
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402
import dados_sintese  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402


def main():
    d = [x for x in dados_sintese.carregar() if x["cover_class"] == "fpv" and x["S_over_phi_n"] is not None]
    med = [x["S_over_phi_n"] for x in d if not x["modelo"]]
    mod = [x["S_over_phi_n"] for x in d if x["modelo"]]
    fat = json.loads((AQUI.parent / "dados_S_phi" / "fatores_supostos.json").read_text(encoding="utf-8"))["fatores"]
    sup, fora = [], 0
    for f in fat:
        if not f["is_pv"] or f["factor"] is None:
            continue
        if f["basis"] == "under_cover_area":
            sup.append(f["factor"])
        elif f["basis"] == "total_water_surface" and f["phi"]:
            sup.append(f["factor"] / f["phi"])
        else:
            fora += 1
    estilo.setup()
    fig, ax = plt.subplots(figsize=(estilo.WIDTH["single"], 76 * estilo.MM), layout="constrained")
    rng = np.random.default_rng(3)
    grupos = [("Measured", med, estilo.SERIES[2]), ("Modelled", mod, estilo.SERIES[0]),
              ("Assumed\n(no measurement)", sup, estilo.SERIES[1])]
    rot = []
    for i, (nome, v, cor) in enumerate(grupos):
        n_est = {"Measured": len({x['grupo'] for x in d if not x['modelo']}),
                 "Modelled": len({x['grupo'] for x in d if x['modelo']})}.get(nome, len(v))
        rot.append(f"{nome}\n{len(v)} / {n_est}")
        if not v:
            continue
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(v)), np.clip(v, -0.2, 2.0), s=16, color=cor,
                   marker=estilo.MARKERS[estilo.SERIES.index(cor)], edgecolor="white", linewidth=0.4, zorder=3)
        m = float(np.median(v))
        ax.plot([i - 0.3, i + 0.3], [m, m], color=estilo.INK, lw=1.4, zorder=4)
        ax.text(i + 0.33, m, f"{m:.2f}", va="center", color=estilo.INK2)
    ax.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
    ax.set_xticks(range(len(grupos)))
    ax.set_xticklabels(rot)
    ax.set_xlabel("values / studies", color=estilo.INK2)
    ax.set_ylabel("Evaporation reduction per unit cover (S/φ)")
    ax.set_ylim(-0.2, 2.0)
    ax.grid(axis="x", visible=False)
    estilo.save(fig, AQUI / "figuras" / "fig07_fpv")
    print(f"measured {len(med)}, modelled {len(mod)}, assumed {len(sup)} (+{fora} without basis or phi); "
          f"medians {np.median(med) if med else None}, {np.median(mod) if mod else None}, {np.median(sup) if sup else None}")


if __name__ == "__main__":
    main()
