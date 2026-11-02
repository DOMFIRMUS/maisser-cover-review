"""Collects the S/phi extraction workflow results into the review dataset.

    python -X utf8 juntar_extracao.py <journal.jsonl> [<journal.jsonl> ...]

Reads the extraction (label extract:*) and verification (label verify:*) agents of each workflow
journal. The verified output is the dataset; the first extraction is kept to report how much the
checking changed. Outputs in dados_S_phi/:
  extracao.json              all studies as verified (later journals override earlier ones)
  S_phi.csv                  one row per condition, with study metadata, S/phi and consistency flags
  estudos_extraidos.csv      one row per study: decision after full text, text used, rows, appraisal
  mudancas_verificacao.csv   every change made by the checker (field, before, after, why)
"""
import ast
import csv
import json
import sys
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "dados_S_phi"
META = DADOS / "textos_completos.csv"


def resultados(journal):
    rotulo, out = {}, {}
    for line in Path(journal).read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("type") == "started":
            rotulo[e["key"]] = e.get("label", "")
        elif e.get("type") == "result":
            v = e.get("result")
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except ValueError:
                    v = ast.literal_eval(v)
            if isinstance(v, dict):
                out[rotulo.get(e["key"], e["key"])] = v
    return out


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def main(journals):
    meta = {r["arquivo_pdf"][:-4]: r for r in csv.DictReader(open(META, encoding="utf-8-sig"))}
    final, primeira, mudancas = {}, {}, []
    for j in journals:
        for rot, v in resultados(j).items():
            alvo = final if rot.startswith("verify:") else primeira if rot.startswith("extract:") else None
            if alvo is None:
                continue
            for s in v.get("studies", []):
                alvo[s["study"]] = s
            if rot.startswith("verify:"):
                mudancas += [dict(c, lote=rot[7:]) for c in v.get("changes", [])]
    for s, v in primeira.items():          # studies whose checker did not finish keep the first extraction
        final.setdefault(s, dict(v, notes=(v.get("notes", "") + " [not verified]").strip()))
    (DADOS / "extracao.json").write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")

    linhas, estudos = [], []
    for s, v in sorted(final.items()):
        m = meta.get(s, {})
        ap = v.get("appraisal") or {}
        rows = v.get("rows") or []
        estudos.append({"study": s, "doi": m.get("doi", ""), "year": m.get("ano", ""), "first_author": m.get("primeiro_autor", ""),
                        "decision": v.get("decision"), "reason": v.get("reason", ""), "text_used": v.get("text_used"),
                        "same_study_as": v.get("same_study_as", ""), "country": v.get("country", ""),
                        "climate": v.get("climate_koppen", ""), "n_rows": len(rows),
                        **{f"rob_{k}": ap.get(k, "") for k in ("control", "phi_definition", "measurement", "period", "gaps_included")},
                        "notes": v.get("notes", "")})
        for k, r in enumerate(rows, 1):
            phi, S, Eo, Ec = num(r.get("phi")), num(r.get("S")), num(r.get("E_o")), num(r.get("E_c"))
            S_E = round(1 - Ec / Eo, 4) if Eo and Ec is not None else None
            flags = []
            if S is None and S_E is not None:
                S = S_E
                flags.append("S from E")
            if S is not None and S_E is not None and abs(S - S_E) > 0.03:
                flags.append(f"S differs from 1-Ec/Eo ({S_E})")
            if phi is not None and not 0 < phi <= 1:
                flags.append("phi out of (0,1]")
            if S is not None and not -0.5 <= S <= 1.0:
                flags.append("S out of range")
            linhas.append({"study": s, "row": k, "doi": m.get("doi", ""), "year": m.get("ano", ""),
                           "decision": v.get("decision"), "same_study_as": v.get("same_study_as", ""),
                           **{c: r.get(c) for c in ("condition", "scale", "water_area_m2", "depth_m", "cover_class",
                                                     "element_size_m", "material", "colour", "mode", "phi", "phi_source",
                                                     "gap_scale_m", "E_o", "E_c", "E_unit", "E_open_ratio", "E_under_ratio")},
                           "S": S, "S_source": r.get("S_source"), "S_basis": r.get("S_basis"),
                           "S_over_phi": round(S / phi, 4) if S is not None and phi else None,
                           **{c: r.get(c) for c in ("period_days", "season", "wind_ms", "wind_height_m", "T_air_C",
                                                     "humidity", "radiation", "method_E", "control", "replication",
                                                     "model_based", "where", "digitised", "confidence", "notes")},
                           "flags": "; ".join(flags)})
    for nome, dados in (("S_phi.csv", linhas), ("estudos_extraidos.csv", estudos),
                        ("mudancas_verificacao.csv", mudancas)):
        if dados:
            cols = list(dict.fromkeys(k for d in dados for k in d))
            with open(DADOS / nome, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, cols)
                w.writeheader()
                w.writerows(dados)
    n1 = sum(len(v.get("rows") or []) for v in primeira.values())
    print(f"{len(final)} studies, {len(linhas)} condition rows ({n1} before checking), {len(mudancas)} changes by the checker")
    from collections import Counter
    print(Counter(v.get("decision") for v in final.values()))


if __name__ == "__main__":
    main(sys.argv[1:])
