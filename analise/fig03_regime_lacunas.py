"""Fig. 3 of the review: what gap diffusion alone does to S/phi (Schlünder's model).

The open water between the elements is treated as circular gaps of radius r, regularly spaced,
under a diffusive boundary layer of thickness delta = D/C_e. Schlünder (1988), written per unit
open area as in Aminzadeh et al. (2018, Eq. 13), gives the enhancement of the evaporation per
unit open area over that of an open surface,

    r_open = 1 / [ theta + (r/delta) sqrt(theta/pi) (sqrt(pi/(4 theta)) - 1) ],   theta = 1 - phi,

which exceeds 1 when the gaps are small compared with delta. The expression is applied where it
predicts enhancement (r_open >= 1); for large gaps the open water evaporates like an open
surface (r_open = 1), as in Aminzadeh et al. (2018). With impermeable elements and no thermal or
aerodynamic effect (r_under = 0), the identity of the review gives

    S = 1 - theta r_open,      S/phi = 1 - (theta/phi)(r_open - 1).

(a) S/phi against phi for several r/delta; (b) S/phi against the diameter of discs in hexagonal
close packing (phi = 0.907; each triangular gap has area 0.0403 d^2, equivalent radius
r = 0.1133 d) for boundary layers of 1, 3 and 10 mm. Gap diffusion alone can only lower S/phi.

    python -X utf8 fig03_regime_lacunas.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

PHI_HEX = np.pi / (2 * np.sqrt(3))          # 0.9069, close packing of equal discs
R_POR_D = np.sqrt((np.sqrt(3) / 4 - np.pi / 8) / np.pi)   # equivalent gap radius / disc diameter


def r_open(phi, r_delta):
    th = 1 - np.asarray(phi, float)
    psi = 1 / (th + r_delta * np.sqrt(th / np.pi) * (np.sqrt(np.pi / (4 * th)) - 1))
    return np.maximum(psi, 1.0)


def s_sobre_phi(phi, r_delta):
    phi = np.asarray(phi, float)
    return (1 - (1 - phi) * r_open(phi, r_delta)) / phi


def main():
    estilo.setup()
    fig, (a, b) = plt.subplots(1, 2, figsize=(estilo.WIDTH["full"], 74 * estilo.MM), layout="constrained")
    cores = [estilo.SEQ[3], estilo.SEQ[6], estilo.SEQ[9], estilo.SEQ[12]]
    linhas = []
    topo = 1.34                               # headroom above S/phi = 1 for the legends

    def referencia(ax, x_texto, texto):
        ax.axhline(1, color=estilo.MUTED, lw=0.8, ls="--")
        ax.text(x_texto, 1.02, texto, color=estilo.INK2, va="bottom")

    # (a) S/phi vs phi
    phi = np.linspace(0.5, PHI_HEX, 300)
    referencia(a, 0.505, "S = φ (area-proportional)")
    for rd, c in zip((0.1, 0.3, 1, 3), cores):
        y = s_sobre_phi(phi, rd)
        a.plot(phi, y, color=c, lw=1.4, label=f"r/δ = {rd:g}")
        a.text(phi[-1] + 0.004, y[-1], f"{rd:g}", color=estilo.INK2, va="center")
        linhas += [("a", rd, p, v) for p, v in zip(phi[::30], y[::30])]
    a.axvline(PHI_HEX, color=estilo.AXIS, lw=0.6, ls=":")
    a.text(PHI_HEX - 0.004, 0.03, "close packing\nof discs", color=estilo.INK2, ha="right", va="bottom")
    a.set_xlim(0.5, 0.95)
    a.set_ylim(0, topo)
    a.set_yticks(np.arange(0, 1.21, 0.2))
    a.set_xlabel("Covered fraction φ")
    a.set_ylabel("Suppression per unit cover, S/φ")
    a.legend(loc="upper left", ncol=4, title="gap radius / boundary-layer thickness",
             columnspacing=1.0, handlelength=1.6, alignment="left")
    estilo.panel_label(a, "a")

    # (b) S/phi vs disc diameter at close packing
    d = np.logspace(-3, 0, 300)
    referencia(b, 1.05, "S = φ: the ceiling for gap diffusion alone")
    for dl, c in zip((1e-3, 3e-3, 1e-2), cores[1:]):
        y = s_sobre_phi(PHI_HEX, R_POR_D * d / dl)
        b.plot(d * 1000, y, color=c, lw=1.4, label=f"δ = {dl * 1000:g} mm")
        linhas += [("b", dl, x, v) for x, v in zip(d[::30], y[::30])]
    b.set_xscale("log")
    b.set_xlim(1, 1000)
    b.set_ylim(0, topo)
    b.set_yticks(np.arange(0, 1.21, 0.2))
    b.set_xlabel("Disc diameter d (mm), hexagonal close packing (φ = 0.907)")
    b.set_ylabel("Suppression per unit cover, S/φ")
    b.legend(loc="upper left", ncol=3, title="boundary-layer thickness",
             columnspacing=1.0, handlelength=1.6, alignment="left")
    estilo.panel_label(b, "b")

    saida = AQUI / "figuras" / "fig03_regime_lacunas"
    estilo.save(fig, saida)
    with open(saida.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["panel", "parameter (r/delta or delta in m)", "x (phi or d in m)", "S_over_phi"])
        w.writerows(linhas)
    for rd in (0.1, 0.3, 1, 3):
        print(f"r/delta={rd:<4g} S/phi at phi=0.75: {s_sobre_phi(0.75, rd):.3f}, at 0.907: {s_sobre_phi(PHI_HEX, rd):.3f}")
    for dd in (0.02, 0.1, 0.2):
        print(f"d={dd*1000:.0f} mm: S/phi = " + ", ".join(f"{s_sobre_phi(PHI_HEX, R_POR_D * dd / dl):.3f} (delta {dl*1000:g} mm)"
                                                     for dl in (1e-3, 3e-3, 1e-2)))


if __name__ == "__main__":
    main()
