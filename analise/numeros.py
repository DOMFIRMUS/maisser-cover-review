"""Single source of the numbers quoted in the review text: writes analise/numeros_sintese.json.

Run after dados_sintese.py, metaregressao.py and fig01_prisma.py. The drafting agents and the final
consistency check read this file instead of copying numbers from earlier drafts.

    python -X utf8 numeros.py
"""
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import dados_sintese  # noqa: E402
from fig01_prisma import contagens  # noqa: E402
from fig04_06_sintese import grupo, GRUPOS  # noqa: E402


def main():
    d = [x for x in dados_sintese.carregar() if x["phi_n"] is not None and x["S_n"] is not None]
    med = [x for x in d if not x["modelo"]]
    sp = [x["S_over_phi_n"] for x in med]
    por_grupo = {}
    for g, (nome, _) in enumerate(GRUPOS):
        v = [x["S_over_phi_n"] for x in med if grupo(x) == g]
        if v:
            por_grupo[nome] = {"conditions": len(v), "studies": len({x["grupo"] for x in med if grupo(x) == g}),
                               "median_S_over_phi": round(statistics.median(v), 2)}
    tab = list(csv.DictReader(open(AQUI / "tabelas" / "tabela4_metaregressao.csv", encoding="utf-8")))
    c = contagens()
    out = {
        "search": {"unique_records": c["unicos"], "queries": dict(c["fontes"]), "screened_title": c["triagem1"],
                   "screened_abstract": c["triagem2"], "awaiting_classification": c["espera"],
                   "assumed_factor": c["assumed"], "insufficient": c["insuf"], "duplicates_found": c["dup"]},
        "full_text": {"sought": c["buscados"], "retrieved": c["obtidos"], "assessed": c["ft_n"],
                      "decisions": dict(c["ft"])},
        "synthesis": {"conditions": len(d), "studies": len({x["grupo"] for x in d}),
                      "by_scale": {k: {"conditions": v, "studies": len({x["grupo"] for x in d if x["classe_escala"] == k})}
                                   for k, v in Counter(x["classe_escala"] for x in d).items()},
                      "measured_conditions": len(med), "measured_studies": len({x["grupo"] for x in med}),
                      "measured_median_S_over_phi": round(statistics.median(sp), 2),
                      "measured_share_below_1": round(sum(v < 1 for v in sp) / len(sp), 2),
                      "by_cover_group": por_grupo},
        "meta_regression": [{k: (round(float(r[k]), 3) if r[k] not in ("", "nan") and k not in ("model", "term")
                                 else r[k]) for k in r} for r in tab],
    }
    (AQUI / "numeros_sintese.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    s = out["synthesis"]
    print(f"synthesis {s['conditions']} conditions / {s['studies']} studies; measured median {s['measured_median_S_over_phi']}, "
          f"below 1: {s['measured_share_below_1']}; full texts {c['obtidos']}/{c['buscados']}")


if __name__ == "__main__":
    main()
