"""Table 4 of the review: mixed-effects meta-regression of S/phi on the measured conditions.

Linear mixed models with a random intercept per study (one study per experiment, from
dados_sintese.py), REML. Covers whose physics differs from area blocking are analysed apart and left
out here: vegetation (transpiration, r_under > 0) and lattice wind barriers (sheltering, S/phi >> 1).
Models: M1 S/phi ~ phi + cover group + field (vs laboratory); M2 adds log10 element size; M3 adds
log10 gap length scale; M4 adds the wind speed at 2 m. Each model uses the conditions that report its
covariates, so n differs between models. Sensitivity: M1 without phi < 0.2 (S/phi unstable).

    python -X utf8 metaregressao.py     # writes tabelas/tabela4_metaregressao.{csv,md}
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import dados_sintese  # noqa: E402
from fig04_06_sintese import grupo, GRUPOS, vento_2m  # noqa: E402

FORA = {"Vegetation and other", "Wind barriers (lattices)"}


def tabela():
    linhas = []
    for x in dados_sintese.carregar():
        if x["modelo"] or x["phi_n"] is None or x["S_n"] is None or x["phi_n"] <= 0:
            continue
        g = GRUPOS[grupo(x)][0]
        if g in FORA:
            continue
        linhas.append({"study": x["grupo"], "S_phi": x["S_over_phi_n"], "phi": x["phi_n"], "cover": g,
                       "field": 1 if x["classe_escala"] == "field" else 0,
                       "log_elem": math.log10(x["elem_n"] * 1000) if x["elem_n"] else np.nan,
                       "log_gap": math.log10(x["gap_n"] * 1000) if x["gap_n"] else np.nan,
                       "wind2": vento_2m(x["wind_n"], dados_sintese.num(x["wind_height_m"]))
                       if x["wind_n"] is not None else np.nan})
    return pd.DataFrame(linhas)


def ajusta(df, formula, nome):
    # L-BFGS can stop at a degenerate point (study variance 0, infinite log-likelihood, unbounded
    # intercept) or raise a singular-matrix error; Powell then finds the finite REML maximum.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = smf.mixedlm(formula, df, groups=df["study"])
        try:
            m = modelo.fit(reml=True, method=["lbfgs"])
            ok = np.isfinite(m.llf) and np.all(np.isfinite(m.bse))
        except (np.linalg.LinAlgError, ValueError):
            ok = False
        if not ok:
            m = modelo.fit(reml=True, method=["powell"])
            if not (np.isfinite(m.llf) and np.all(np.isfinite(m.bse))):
                raise np.linalg.LinAlgError("no finite REML maximum")
    ci = m.conf_int()
    out = []
    for k in m.fe_params.index:
        out.append({"model": nome, "term": k, "estimate": m.fe_params[k], "ci_low": ci.loc[k, 0],
                    "ci_high": ci.loc[k, 1], "p": m.pvalues[k]})
    out.append({"model": nome, "term": "study variance", "estimate": float(m.cov_re.iloc[0, 0]),
                "ci_low": np.nan, "ci_high": np.nan, "p": np.nan})
    out.append({"model": nome, "term": "residual variance", "estimate": m.scale, "ci_low": np.nan,
                "ci_high": np.nan, "p": np.nan})
    return out, len(df), df["study"].nunique()


def main():
    df = tabela()
    base = "S_phi ~ phi + C(cover, Treatment('Floating elements')) + field"
    specs = [("M1", base, df),
             ("M1, phi >= 0.2", base, df[df.phi >= 0.2]),
             ("M2", base + " + log_elem", df.dropna(subset=["log_elem"])),
             ("M3", base + " + log_gap", df.dropna(subset=["log_gap"])),
             ("M4", base + " + wind2", df.dropna(subset=["wind2"]))]
    rows, resumo = [], []
    for nome, f, d in specs:
        if d["field"].nunique() < 2:
            f = f.replace(" + field", "")
        try:
            r, n, k = ajusta(d, f, nome)
        except Exception:                                       # covariate collinear with the cover groups
            f = "S_phi ~ phi + " + f.split(" + ")[-1]
            nome += " (phi + covariate only)"
            try:
                r, n, k = ajusta(d, f, nome)
            except Exception as e:
                resumo.append(f"{nome}: not estimable ({type(e).__name__})")
                continue
        rows += r
        resumo.append(f"{nome}: {n} conditions, {k} studies")
    t = pd.DataFrame(rows)
    (AQUI / "tabelas").mkdir(exist_ok=True)
    t.to_csv(AQUI / "tabelas" / "tabela4_metaregressao.csv", index=False)
    md = ["| Model | Term | Estimate | 95 % CI | p |", "|---|---|---|---|---|"]
    for _, r in t.iterrows():
        term = (r["term"].replace("C(cover, Treatment('Floating elements'))[T.", "cover: ").replace("]", "")
                .replace("log_elem", "log10 element size (mm)").replace("log_gap", "log10 gap scale (mm)")
                .replace("wind2", "wind speed at 2 m (m s-1)").replace("field", "field scale (vs laboratory)"))
        ci = "" if pd.isna(r["ci_low"]) else f"{r['ci_low']:.2f} to {r['ci_high']:.2f}"
        p = "" if pd.isna(r["p"]) else ("< 0.001" if r["p"] < 0.001 else f"{r['p']:.3f}")
        md.append(f"| {r['model']} | {term} | {r['estimate']:.3f} | {ci} | {p} |")
    (AQUI / "tabelas" / "tabela4_metaregressao.md").write_text("\n".join(md) + "\n\n" + "; ".join(resumo) + "\n",
                                                             encoding="utf-8")
    print("\n".join(resumo))
    print(t[t.model == "M1"][["term", "estimate", "ci_low", "ci_high", "p"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
