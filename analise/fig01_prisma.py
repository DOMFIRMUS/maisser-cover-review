"""Fig. 1 of the review: PRISMA 2020 flow, with every count read from the review files.

Sources: busca/brutos/registro_consultas.jsonl (queries), busca/candidatos.csv (records and
screening decisions), dados_S_phi/textos_completos.csv and textos/ (retrieval) and
dados_S_phi/estudos_extraidos.csv (full-text decisions). Rerun whenever any of them changes.

    python -X utf8 fig01_prisma.py
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import estilo_revisao as estilo  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402


def contagens():
    q = [json.loads(l) for l in open(RAIZ / "busca" / "brutos" / "registro_consultas.jsonl", encoding="utf-8")]
    # a query rerun under the same id (the Scopus queries were first run capped at 200 records) counts once,
    # with its last run; SC0 was a syntax test of the Scopus API
    ult = {}
    for x in q:
        if not (x.get("tag") == "S8" and x.get("id") == "SC0"):
            ult[(x.get("tag"), x.get("id"), x.get("source"))] = x
    q = list(ult.values())
    rec = list(csv.DictReader(open(RAIZ / "busca" / "candidatos.csv", encoding="utf-8-sig")))
    dec = Counter(r["decision"] for r in rec)
    lista = list(csv.DictReader(open(RAIZ / "dados_S_phi" / "textos_completos.csv", encoding="utf-8-sig")))
    if (RAIZ / "textos").is_dir():
        obtidos = [r for r in lista if (RAIZ / "textos" / r["arquivo_pdf"]).exists()]
    else:   # public deposit: the PDFs are not redistributed; dados_S_phi/textos_obtidos.txt names them
        nomes = set((RAIZ / "dados_S_phi" / "textos_obtidos.txt").read_text(encoding="utf-8").splitlines())
        obtidos = [r for r in lista if r["arquivo_pdf"] in nomes]
    ext = RAIZ / "dados_S_phi" / "estudos_extraidos.csv"
    ft = Counter(r["decision"] for r in csv.DictReader(open(ext, encoding="utf-8-sig"))) if ext.exists() else Counter()
    rotulo = {k[len("not screened: "):]: v for k, v in dec.items() if k.startswith("not screened: ")}
    c = {
        "fontes": Counter(x["source"] for x in q),
        "retornados": sum(int(x.get("returned") or 0) for x in q),
        "unicos": len(rec),
        "rotulo": rotulo, "rotulo_n": sum(rotulo.values()),
        "triagem1": sum(1 for r in rec if r["stage1"]),
        "espera": sum(1 for r in rec if r["stage1"] == "K" and not r["decision"]),
        "t1_exc": dec["exclude (stage 1)"], "t1_ctx": dec["context_only (stage 1)"],
        "triagem2": sum(dec[k] for k in ("include", "include_model", "assumed", "insufficient", "context_only",
                                         "exclude", "duplicate")),
        "assumed": dec["assumed"], "insuf": dec["insufficient"], "ctx": dec["context_only"], "exc": dec["exclude"],
        "dup": dec["duplicate"], "buscados": len(lista), "obtidos": len(obtidos),
        "ft": ft, "ft_n": sum(ft.values()),
    }
    c["duplicados"] = c["retornados"] - c["unicos"]
    return c


def caixa(ax, x, y, w, h, texto, forte=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                fc=estilo.SEQ[0] if forte else "white", ec=estilo.AXIS, lw=0.7))
    ax.text(x + 0.012, y + h / 2, texto, va="center", ha="left", color=estilo.INK, linespacing=1.3)


def seta(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", lw=0.7, color=estilo.INK2, shrinkA=0, shrinkB=0,
                                mutation_scale=7))


def main():
    c = contagens()
    estilo.setup()
    fig = plt.figure(figsize=(estilo.WIDTH["full"], 165 * estilo.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    itens = [f"{k} ({v} queries)" for k, v in c["fontes"].most_common()]
    fontes = ",\n".join(", ".join(itens[k:k + 2]) for k in range(0, len(itens), 2))
    r = c["rotulo"]
    ft = c["ft"]
    medidos, modelados = ft.get("include", 0), ft.get("include_model", 0)
    fora = {k: v for k, v in ft.items() if k not in ("include", "include_model")}
    esq = [
        (f"Records retrieved by the search\n{fontes}\nn = {c['retornados']:,}", True),
        (f"Unique records labelled during the search\nn = {c['unicos']:,}", False),
        (f"Records screened on title and abstract snippet\nn = {c['triagem1']:,}", False),
        (f"Records screened on the full abstract\nn = {c['triagem2']:,}", False),
        (f"Reports sought for retrieval\nn = {c['buscados']:,}", False),
        (f"Reports assessed at full text\nn = {c['ft_n']:,}", False),
        (f"Studies in the S/φ synthesis\nmeasured n = {medidos}; modelled n = {modelados}", True),
    ]
    dir_ = [
        f"Duplicates removed: n = {c['duplicados']:,}",
        (f"Out of scope for the dataset by label: n = {c['rotulo_n']}\n"
         f"(other topics {r.get('other', 0)}, theory {r.get('theory', 0)}, reviews {r.get('review', 0)}, "
         f"models without S {r.get('model_study', 0)},\nmonolayers {r.get('monolayer_continuous', 0)}, "
         f"primary without data {sum(v for k, v in r.items() if k.startswith('primary'))});\n"
         "theory and reviews used as context"),
        f"Excluded: n = {c['t1_exc']}; context only: n = {c['t1_ctx']}"
        + (f"\nkept but awaiting an abstract (Scopus, university network): n = {c['espera']}" if c["espera"] else ""),
        (f"Reduction only assumed: n = {c['assumed']} (analysed separately)\n"
         f"insufficient: n = {c['insuf']}; context only: n = {c['ctx']}; excluded: n = {c['exc']};\n"
         f"duplicates found at full text: n = {c['dup']}"),
        f"Not yet retrieved: n = {c['buscados'] - c['obtidos']}",
        ("Not in the synthesis:\n" + "\n".join(
            "; ".join(itens[k:k + 3]) for itens in [[f"{a.replace('_', ' ')} {v}" for a, v in sorted(fora.items())]]
            for k in range(0, len(itens), 3)) if fora else "Not in the synthesis: -"),
        "",
    ]
    n = len(esq)
    h, gap = 0.108, (0.96 - 0.04) / n
    xl, wl, xr, wr = 0.04, 0.40, 0.50, 0.48
    ys = [0.96 - (i + 1) * gap + (gap - h) / 2 for i in range(n)]
    for i, ((t, forte), td) in enumerate(zip(esq, dir_)):
        caixa(ax, xl, ys[i], wl, h, t, forte)
        if td:
            caixa(ax, xr, ys[i], wr, h, td)
            seta(ax, xl + wl, ys[i] + h / 2, xr, ys[i] + h / 2)
        if i < n - 1:
            seta(ax, xl + wl / 2, ys[i], xl + wl / 2, ys[i + 1] + h)
    estilo.save(fig, AQUI / "figuras" / "fig01_prisma")
    print(json.dumps({k: (dict(v) if isinstance(v, Counter) else v) for k, v in c.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
