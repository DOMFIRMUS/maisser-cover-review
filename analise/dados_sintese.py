"""Synthesis table of the review: one study per experiment, conditions with S and phi on the whole surface.

Reads dados_S_phi/S_phi.csv (all extracted conditions) and dados_S_phi/grupos_estudo.json (reports of
the same experiment). Keeps the studies in the synthesis (decision include or include_model) and, in a
group of reports, only the principal one. Adds the study group, the scale class and model flag.

    python -X utf8 dados_sintese.py      # writes dados_S_phi/S_phi_sintese.csv and prints a summary

Other scripts import carregar().
"""
import csv
import json
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados_S_phi"
LAB = {"pan", "tank", "wind_tunnel", "other"}
CAMPO = {"pond", "dam", "reservoir", "lake"}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def grupos():
    g = json.loads((DADOS / "grupos_estudo.json").read_text(encoding="utf-8"))["grupos"]
    membro = {r: x for x in g for r in x["relatos"]}
    return membro


def adicionais():
    """(study, row) of linked reports that the reconciliation step added to their experiment."""
    p = DADOS / "conciliacao" / "decisoes.json"
    if not p.exists():
        return set()
    return {(a["study"], str(a["row"])) for d in json.loads(p.read_text(encoding="utf-8")) for a in d["adicionar"]}


def carregar(apenas_total=True):
    """Rows of the synthesis: list of dicts with numeric phi, S, S_over_phi and the study group."""
    membro, extra = grupos(), adicionais()
    cfg = json.loads((DADOS / "grupos_estudo.json").read_text(encoding="utf-8"))
    fora = {(s, str(i)) for s, v in cfg.get("excluir_linhas", {}).items() if not s.startswith("_") for i in v}
    aud = DADOS / "conciliacao" / "auditoria_replicacao.json"
    if aud.exists():   # sub-periods, monthly parts and duplicate panels of conditions already counted (30/10/2026)
        fora |= {(x["study"], str(x["row"])) for x in json.loads(aud.read_text(encoding="utf-8"))["excluir"]}
    separado = {(x["study"], str(i)): x["grupo"] for x in cfg.get("estudos_separados", []) for i in x["linhas"]}
    out = []
    for r in csv.DictReader(open(DADOS / "S_phi.csv", encoding="utf-8-sig")):
        g = membro.get(r["study"])
        chave = (r["study"], r["row"])
        if chave in fora:
            continue                               # alternative analysis of a condition already counted
        if chave in separado:
            g = {"grupo": separado[chave], "principal": r["study"]}   # a different experiment in the same report
        elif chave in extra:
            pass                                   # condition of a linked report missing from the principal one
        elif r["decision"] not in ("include", "include_model") or (g and g["principal"] != r["study"]):
            continue
        phi, s = num(r["phi"]), num(r["S"])
        if apenas_total and r["S_basis"] != "total_surface":
            continue
        modelo = r["model_based"] == "True" or r["decision"] == "include_model" or r["scale"] == "model_only"
        out.append({**r, "grupo": g["grupo"] if g else r["study"], "phi_n": phi, "S_n": s,
                    "S_over_phi_n": s / phi if (s is not None and phi) else None,
                    "classe_escala": "model" if modelo else ("lab" if r["scale"] in LAB else
                                                             "field" if r["scale"] in CAMPO else "other"),
                    "modelo": modelo, "wind_n": num(r["wind_ms"]), "gap_n": num(r["gap_scale_m"]),
                    "elem_n": num(r["element_size_m"])})
    return out


def main():
    d = carregar()
    cols = list(d[0].keys())
    with open(DADOS / "S_phi_sintese.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(d)
    com = [x for x in d if x["phi_n"] is not None and x["S_n"] is not None]
    print(f"{len(d)} conditions from {len({x['grupo'] for x in d})} studies; {len(com)} with phi and S "
          f"({len({x['grupo'] for x in com})} studies)")
    print("by scale class (conditions, studies):",
          {k: (v, len({x['grupo'] for x in com if x['classe_escala'] == k})) for k, v in
           Counter(x["classe_escala"] for x in com).items()})
    print("by cover class:", dict(Counter(x["cover_class"] for x in com).most_common()))
    print("with wind:", sum(1 for x in com if x["wind_n"] is not None), "| with gap scale:",
          sum(1 for x in com if x["gap_n"] is not None), "| with element size:",
          sum(1 for x in com if x["elem_n"] is not None))
    sp = sorted(x["S_over_phi_n"] for x in com if x["classe_escala"] != "model")
    if sp:
        print(f"measured S/phi: median {sp[len(sp) // 2]:.2f}, share below 1: {sum(v < 1 for v in sp) / len(sp):.2f}")


if __name__ == "__main__":
    main()
