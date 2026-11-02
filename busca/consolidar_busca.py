"""Merges the search-agent outputs, redoes lost queries, fetches abstracts and builds screening batches.

    python -X utf8 consolidar_busca.py refazer-s3              # rerun the FPV queries whose results were lost
    python -X utf8 consolidar_busca.py lotes1                  # merge, abstracts, prefilter, stage-1 batches
    python -X utf8 consolidar_busca.py lotes2 <journal.jsonl>  # stage-1 decisions -> stage-2 batches
    python -X utf8 consolidar_busca.py pendentes               # new unscreened records -> lotes/lote_pendentes.md
    python -X utf8 consolidar_busca.py juntar <journal.jsonl>  # stage-2 decisions -> triagem.json, CSV
    python -X utf8 consolidar_busca.py csv                     # rewrite CSVs (ajustes_manuais.json applied)

Outputs (in brutos/): candidatos.json (deduplicated records), resumos.json (OpenAlex abstracts by
DOI), lotes1/ (title screening, one line per record), triagem1.json (K keep / C context / D drop),
lotes/lote_NN.md (full-abstract batches), triagem.json (decisions) and ../candidatos.csv.
"""
import csv
import json
import re
import sys
from pathlib import Path

import busca_api as api

BRUTOS = Path(__file__).resolve().parent / "brutos"
PRIMARY = {"primary_lab", "primary_field", "primary_fpv", "model_study", "monolayer_continuous", "scopus_unlabelled"}
LOTE = 72


def key_of(c):
    d = api.bare(c.get("doi", "")).lower()
    return "doi:" + d if d else "tit:" + re.sub(r"[^a-z0-9]", "", (c.get("title") or "").lower())[:60]


def words(t):
    return set(re.findall(r"[a-z0-9]{3,}", (t or "").lower()))


def oa_batch(dois):
    """OpenAlex records (with abstract) for a list of DOIs, 50 per call."""
    sel = api.OA_SELECT + ",abstract_inverted_index"
    out = {}
    for k in range(0, len(dois), 50):
        d = api.get("https://api.openalex.org/works",
                    {"filter": "doi:" + "|".join(dois[k:k + 50]), "per-page": 50, "select": sel}, api.oa_key())
        for w in d.get("results", []):
            out[api.bare(w.get("doi")).lower()] = w
    return out


def compact(w):
    au = w.get("authorships") or []
    loc = w.get("best_oa_location") or {}
    return {"title": w.get("display_name") or "", "year": w.get("publication_year") or 0,
            "first_author": au[0]["author"]["display_name"] if au else "",
            "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
            "abstract": api.abstract_of(w.get("abstract_inverted_index")),
            "oa_url": (loc.get("pdf_url") or loc.get("landing_page_url") or "") if (w.get("open_access") or {}).get("is_oa") else ""}


def refazer_s3():
    """Rerun the OpenAlex queries of the FPV stratum (their results were lost when the agent stopped)."""
    s3 = json.loads((BRUTOS / "S3_fotovoltaica.json").read_text(encoding="utf-8"))
    sel = api.OA_SELECT + ",abstract_inverted_index"
    cands, resumos = [], {}
    for q in s3["queries"]:
        text = q["query"]
        m = re.match(r"(cites|refs):(\S+)", text)
        if m and m.group(1) == "cites":
            w = oa_batch([api.bare(m.group(2))])
            wid = next(iter(w.values()))["id"].rsplit("/", 1)[-1]
            d = api.get("https://api.openalex.org/works", {"filter": f"cites:{wid}", "per-page": 200, "select": sel}, api.oa_key())
            works = d.get("results", [])
        elif m:
            w = oa_batch([api.bare(m.group(2))])
            wid = next(iter(w.values()))["id"].rsplit("/", 1)[-1]
            full = api.get("https://api.openalex.org/works/" + wid, {"select": "id,referenced_works"}, api.oa_key())
            ids = [r.rsplit("/", 1)[-1] for r in full.get("referenced_works", [])]
            works = []
            for k in range(0, len(ids), 50):
                works += api.get("https://api.openalex.org/works", {"filter": "openalex_id:" + "|".join(ids[k:k + 50]),
                                 "per-page": 50, "select": sel}, api.oa_key()).get("results", [])
        else:
            d = api.get("https://api.openalex.org/works", {"filter": "title_and_abstract.search:" + text.replace(",", " "),
                        "per-page": 200, "select": sel}, api.oa_key())
            works = d.get("results", [])
        kept = 0
        for w in works:
            c = compact(w)
            txt = (c["title"] + " " + c["abstract"]).lower()
            if "evapor" not in txt and "water saving" not in txt:
                continue
            kept += 1
            doi = api.bare(w.get("doi")).lower()
            fpv = any(s in txt for s in ("photovolta", "solar", "fpv", "pv "))
            cands.append({"doi": doi, "title": c["title"], "year": c["year"], "first_author": c["first_author"],
                          "venue": c["venue"], "doc_type": "journal",
                          "category": "primary_fpv" if fpv else "other", "scale": "reservoir",
                          "cover_class": "FPV" if fpv else "", "quantitative_S_phi": "maybe",
                          "found_by": "S3R-" + q["id"], "note": "machine rerun of the FPV query; not yet screened"})
            if doi:
                resumos[doi] = c
        print(f"{q['id']}: {len(works)} records, {kept} mention evaporation/water saving")
    out = {"stratum": "S3 floating photovoltaics (machine rerun of the agent's OpenAlex queries)",
           "date": s3.get("date"), "queries": s3["queries"], "candidates": cands,
           "coverage_note": "Records kept only if title/abstract mentions evaporation or water saving; screened later."}
    (BRUTOS / "S3R_fotovoltaica_refeita.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    p = BRUTOS / "resumos.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    p.write_text(json.dumps({**old, **resumos}, ensure_ascii=False), encoding="utf-8")
    print(f"S3R: {len(cands)} candidates")


# Scopus rerun (stratum S8, 2026-10-29): the same questions as strata S1-S6 in Scopus syntax. Scopus
# does not accept AND and W/n inside one TITLE-ABS-KEY(), so each concept is a separate field clause.
SCOPUS = [
    ("SC1", "floating elements on water",
     'TITLE-ABS-KEY(evaporat*) AND TITLE-ABS-KEY(floating W/3 (cover* OR ball* OR disc* OR disk* OR element* OR '
     'module* OR hexagon* OR plate* OR raft* OR sheet*))'),
    ("SC2", "suspended covers and shade cloth",
     'TITLE-ABS-KEY(evaporat*) AND TITLE-ABS-KEY("shade cloth*" OR "shade net*" OR "shading net*" OR '
     '"suspended cover*" OR "shade structure*")'),
    ("SC3", "floating photovoltaics",
     'TITLE-ABS-KEY("floating photovoltaic*" OR "floating PV" OR "floating solar" OR floatovoltaic* OR '
     '"floating solar panel*") AND TITLE-ABS-KEY(evaporat* OR "water saving*" OR "water conservation")'),
    ("SC4", "shade balls and floating balls",
     'TITLE-ABS-KEY("shade ball*" OR "plastic ball*" OR "hollow ball*" OR "floating ball*") AND '
     'TITLE-ABS-KEY(evaporat*)'),
    ("SC5", "covers on reservoirs, ponds, tanks and canals",
     'TITLE-ABS-KEY(evaporat* W/3 (suppress* OR reduc* OR mitigat* OR control* OR prevent* OR sav*)) AND '
     'TITLE-ABS-KEY(cover* OR covering*) AND TITLE-ABS-KEY(reservoir* OR pond* OR dam OR dams OR tank* OR pan OR '
     '"water storage*" OR canal*)'),
    ("SC6", "partially covered water surfaces",
     'TITLE-ABS-KEY(evaporat*) AND TITLE-ABS-KEY("partially covered" OR "partial cover*" OR "perforated cover*" '
     'OR "covered fraction" OR "coverage ratio" OR "surface coverage") AND TITLE-ABS-KEY(water)'),
    ("SC7", "reviews of evaporation suppression",
     'TITLE-ABS-KEY(evaporat* W/3 (suppress* OR reduc* OR mitigat* OR control*)) AND '
     'TITLE-ABS-KEY(review OR overview OR "state of the art") AND TITLE-ABS-KEY(reservoir* OR "water bod*" OR '
     '"water storage*")'),
    ("SC8", "canal-top photovoltaics",
     'TITLE-ABS-KEY("canal-top" OR "over-canal" OR "canal top") AND TITLE-ABS-KEY(evaporat*)'),
    ("SC9", "floating covers and the water energy balance",
     'TITLE-ABS-KEY("floating cover*" OR "floating element*" OR "floating module*") AND '
     'TITLE-ABS-KEY("water temperature" OR "energy balance" OR heat)'),
]


def scopus(n=500):
    """Run the Scopus queries (at most n records each) and write brutos/S8_scopus.json."""
    import argparse
    cands, qs = [], []
    for qid, desc, q in SCOPUS:
        res = api.sc_lista(q, n)
        api.log(argparse.Namespace(tag="S8", id=qid, cmd="sc"), "Scopus", q, res["total"], len(res["itens"]))
        qs.append({"id": qid, "description": desc, "query": q, "hits": res["total"], "retrieved": len(res["itens"])})
        for it in res["itens"]:
            cands.append({"doi": it["doi"], "title": it["title"], "year": int(it["year"] or 0),
                          "first_author": it["first_author"], "venue": it["venue"], "doc_type": it["type"],
                          "category": "scopus_unlabelled", "scale": "", "cover_class": "",
                          "quantitative_S_phi": "maybe", "found_by": "S8-" + qid, "note": ""})
        print(f"{qid} {desc}: {res['total']} hits, {len(res['itens'])} retrieved"
              + (f" (capped at {n})" if res["total"] > n else ""))
    out = {"stratum": "S8 Scopus rerun of the review questions (Scopus Search API, Elsevier key)",
           "date": __import__("datetime").date.today().isoformat(), "queries": qs, "candidates": cands,
           "coverage_note": f"At most {n} records per query, in Scopus relevance order; unlabelled records go to "
                            "stage-2 screening unless they were already found by another stratum."}
    (BRUTOS / "S8_scopus.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"S8: {len(cands)} records from {len(qs)} queries")


def merge():
    recs = {}
    for f in sorted(BRUTOS.glob("S*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        stratum = f.stem.split("_")[0]
        for c in d.get("candidates", []):
            k = key_of(c)
            if k in recs:
                r = recs[k]
                r["strata"] = sorted(set(r["strata"]) | {stratum})
                r["found_by"] += ";" + c.get("found_by", "")
                if c.get("quantitative_S_phi") == "yes" or (c.get("quantitative_S_phi") == "maybe" and r["quantitative_S_phi"] == "no"):
                    r["quantitative_S_phi"] = c["quantitative_S_phi"]
                if r["category"] not in PRIMARY and c.get("category") in PRIMARY:
                    r["category"] = c["category"]
                if len(c.get("note") or "") > len(r.get("note") or ""):
                    r["note"] = c["note"]
            else:
                recs[k] = {**c, "doi": api.bare(c.get("doi", "")).lower(), "key": k, "strata": [stratum]}
    return recs


WATER_BODY = re.compile(r"floating|fpv|floatovolta|aquavolta|fishery|reservoir|lake|pond|canal|dam\b|dams\b|water surface|water bod")


def preparar():
    """Merge, fetch missing abstracts, check titles, apply the rule prefilter; write candidatos.json."""
    recs = merge()
    p = BRUTOS / "resumos.json"
    resumos = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    falta = [r["doi"] for r in recs.values() if r["doi"] and r["doi"] not in resumos]
    for doi, w in oa_batch(falta).items():
        resumos[doi] = compact(w)
    p.write_text(json.dumps(resumos, ensure_ascii=False), encoding="utf-8")
    nrule = 0
    for r in recs.values():
        oa = resumos.get(r["doi"])
        r["in_openalex"] = bool(oa)
        r["title_match"] = round(len(words(r["title"]) & words(oa["title"])) / max(1, len(words(r["title"]) | words(oa["title"]))), 2) if oa else None
        r["oa_url"] = oa["oa_url"] if oa else ""
        if r["strata"] == ["S3R"] and r["category"] in PRIMARY:
            txt = (r["title"] + " " + (oa or {}).get("abstract", "")).lower()
            if not WATER_BODY.search(txt):
                r["category"], r["note"] = "other", "rule prefilter: no water-body term in title/abstract"
                nrule += 1
    (BRUTOS / "candidatos.json").write_text(json.dumps(list(recs.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    return recs, resumos, nrule


def to_screen(recs):
    return sorted((r for r in recs.values() if r.get("quantitative_S_phi") != "no" and r.get("category") in PRIMARY),
                  key=lambda r: (r["category"], r.get("year") or 0))


def lotes1():
    """Merge, fetch abstracts, apply the rule prefilter and write one-line-per-record batches (stage 1)."""
    recs, resumos, nrule = preparar()
    tri = to_screen(recs)
    d = BRUTOS / "lotes1"
    d.mkdir(exist_ok=True)
    for f in d.glob("*.md"):
        f.unlink()
    size = 110
    for n, i in enumerate(range(0, len(tri), size), 1):
        lines = []
        for r in tri[i:i + size]:
            ab = (resumos.get(r["doi"], {}).get("abstract") or "").replace("\n", " ")[:320]
            lines.append(f"{r['key']} || {r.get('year')} | {r.get('first_author', '')} | {r['title']} | {r.get('venue', '')} "
                         f"|| abs: {ab or 'none'}")
        (d / f"lote1_{n:02d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(recs)} unique records; rule prefilter removed {nrule} machine FPV records; "
          f"{len(tri)} to screen in {n} stage-1 batches; "
          f"{sum(1 for r in recs.values() if r['doi'] and not r['in_openalex'])} DOIs not in OpenAlex")


def decisions(journal, field="decisions"):
    out = {}
    for line in Path(journal).read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("type") != "result":
            continue
        val = e.get("result") if isinstance(e.get("result"), dict) else e.get("value")
        if isinstance(val, dict):
            for x in val.get(field, []):
                out[x["key"]] = x
    return out


def escrever_lote(path, recs, resumos):
    """Stage-2 batch: one block per record with metadata, warnings and the abstract."""
    lines = []
    for r in recs:
        oa = resumos.get(r["doi"], {})
        lines.append(f"### {r['key']}")
        lines.append(f"{r['title']} | {r.get('year')} | {r.get('first_author', '')} | {r.get('venue', '')} | "
                     f"search label: {r['category']}, {r.get('scale', '')}, {r.get('cover_class', '')}")
        if r.get("note"):
            lines.append("search note: " + r["note"])
        if oa and r["title_match"] is not None and r["title_match"] < 0.5:
            lines.append(f"WARNING: the DOI resolves to a different title in OpenAlex: {oa['title']} ({oa['year']})")
        if not r["doi"]:
            lines.append("no DOI (grey literature or not in OpenAlex)")
        elif not oa:
            lines.append("DOI not found in OpenAlex")
        if oa.get("oa_url"):
            lines.append("open access: " + oa["oa_url"])
        lines.append("abstract: " + ((oa.get("abstract") or "")[:1100] or "none"))
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def pendentes():
    """Records added after the screening runs (e.g. by the critic) go straight to a stage-2 batch."""
    recs, resumos, _ = preparar()
    feitos = set()
    for f in ("triagem1.json", "triagem.json"):
        p = BRUTOS / f
        if p.exists():
            feitos |= set(json.loads(p.read_text(encoding="utf-8")))
    pend = [r for r in to_screen(recs) if r["key"] not in feitos]
    for f in (BRUTOS / "lotes").glob("lote_p*.md"):
        f.unlink()
    n = 0
    for i in range(0, len(pend), LOTE):
        n += 1
        escrever_lote(BRUTOS / "lotes" / f"lote_p{n:02d}.md", pend[i:i + LOTE], resumos)
    print(f"{len(recs)} unique records; {len(pend)} new records to screen in lotes/lote_p01..p{n:02d}.md")


def lotes1_pendentes():
    """Stage-1 one-line batches (lotes1/lote1_pNN.md) for records not yet screened (e.g. the Scopus stratum)."""
    recs = {r["key"]: r for r in json.loads((BRUTOS / "candidatos.json").read_text(encoding="utf-8"))}
    resumos = json.loads((BRUTOS / "resumos.json").read_text(encoding="utf-8"))
    feitos = set()
    for f in ("triagem1.json", "triagem.json"):
        q = BRUTOS / f
        if q.exists():
            feitos |= set(json.loads(q.read_text(encoding="utf-8")))
    pend = [r for r in to_screen(recs) if r["key"] not in feitos]
    d = BRUTOS / "lotes1"
    for f in d.glob("lote1_p*.md"):
        f.unlink()
    n = 0
    for i in range(0, len(pend), 110):
        n += 1
        lines = []
        for r in pend[i:i + 110]:
            ab = (resumos.get(r["doi"], {}).get("abstract") or "").replace("\n", " ")[:320]
            lines.append(f"{r['key']} || {r.get('year')} | {r.get('first_author', '')} | {r['title']} | "
                         f"{r.get('venue', '')} || abs: {ab or 'none'}")
        (d / f"lote1_p{n:02d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(pend)} records not yet screened in lotes1/lote1_p01..p{n:02d}.md "
          f"({sum(1 for r in pend if not resumos.get(r['doi'], {}).get('abstract'))} without abstract)")


def lotes2_pendentes(journal):
    """Stage-1 decisions of the pending records -> stage-2 batches lotes/lote_qNN.md for the new K records.

    K records without any abstract go to lotes/sem_resumo.md instead: their abstract (mostly Elsevier, via
    Scopus) can only be fetched from the university network, and they are screened when it is available."""
    d1 = decisions(journal)
    p = BRUTOS / "triagem1.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update(d1)
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    recs = {r["key"]: r for r in json.loads((BRUTOS / "candidatos.json").read_text(encoding="utf-8"))}
    resumos = json.loads((BRUTOS / "resumos.json").read_text(encoding="utf-8"))
    t2 = json.loads((BRUTOS / "triagem.json").read_text(encoding="utf-8"))
    novos = [recs[k] for k, x in d1.items() if x.get("d") == "K" and k in recs and k not in t2]
    com = [r for r in novos if resumos.get(r["doi"], {}).get("abstract")]
    sem = [r for r in novos if r not in com]
    d = BRUTOS / "lotes"
    for f in d.glob("lote_q*.md"):
        f.unlink()
    n = 0
    for i in range(0, len(com), LOTE):
        n += 1
        escrever_lote(d / f"lote_q{n:02d}.md", com[i:i + LOTE], resumos)
    escrever_lote(d / "sem_resumo.md", sem, resumos)
    print(f"stage 1: {len(d1)} new decisions ({sum(1 for x in d1.values() if x.get('d') == 'K')} K); "
          f"{len(com)} K with abstract in lote_q01..q{n:02d}.md; {len(sem)} K without abstract in sem_resumo.md")


def lotes2(journal):
    """Read stage-1 decisions and write full-abstract batches (stage 2) for the records kept."""
    d1 = decisions(journal)
    p = BRUTOS / "triagem1.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update(d1)
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    recs = {r["key"]: r for r in json.loads((BRUTOS / "candidatos.json").read_text(encoding="utf-8"))}
    resumos = json.loads((BRUTOS / "resumos.json").read_text(encoding="utf-8"))
    tri = sorted((recs[k] for k, x in old.items() if x.get("d") == "K" and k in recs),
                 key=lambda r: (r["category"], r.get("year") or 0))
    d = BRUTOS / "lotes"
    d.mkdir(exist_ok=True)
    for f in d.glob("lote_*.md"):
        f.unlink()
    n = 0
    for i in range(0, len(tri), LOTE):
        n += 1
        escrever_lote(d / f"lote_{n:02d}.md", tri[i:i + LOTE], resumos)
    print(f"stage 1: {len(old)} decisions ({sum(1 for x in old.values() if x.get('d') == 'K')} K, "
          f"{sum(1 for x in old.values() if x.get('d') == 'C')} C, {sum(1 for x in old.values() if x.get('d') == 'D')} D); "
          f"{len(tri)} records in {n} stage-2 batches; "
          f"{sum(1 for r in tri if r['title_match'] is not None and r['title_match'] < 0.5)} title mismatches")


def juntar(journal):
    """Collect stage-2 decisions from a workflow journal and write triagem.json and candidatos.csv."""
    dec = decisions(journal)
    p = BRUTOS / "triagem.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update(dec)
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    escrever_csv(old)
    print(f"{len(dec)} decisions read; {len(old)} in triagem.json")


def escrever_csv(old=None):
    """candidatos.csv = every record with its screening outcome; manual adjustments applied last."""
    if old is None:
        old = json.loads((BRUTOS / "triagem.json").read_text(encoding="utf-8"))
    aj = json.loads((BRUTOS / "ajustes_manuais.json").read_text(encoding="utf-8"))
    old = {k: {**v, **aj.get(k, {})} for k, v in old.items()}
    recs = json.loads((BRUTOS / "candidatos.json").read_text(encoding="utf-8"))
    t1 = json.loads((BRUTOS / "triagem1.json").read_text(encoding="utf-8"))
    cols = ["key", "doi", "year", "first_author", "title", "venue", "category", "scale", "cover_class",
            "quantitative_S_phi", "strata", "found_by", "in_openalex", "title_match", "oa_url",
            "decision", "stage1", "why", "where", "phi", "S", "n", "pr", "mismatch", "manual"]
    s1 = {"C": "context_only (stage 1)", "D": "exclude (stage 1)"}
    with open(BRUTOS.parent / "candidatos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            x, d1 = old.get(r["key"], {}), t1.get(r["key"], {}).get("d", "")
            decision = x.get("dec") or s1.get(d1) or ("" if d1 else "not screened: " + r["category"])
            w.writerow({**r, "strata": ";".join(r["strata"]), "decision": decision, "stage1": d1,
                        **{k: x.get(k, "") for k in cols[17:]}})


def textos():
    """dados_S_phi/textos_completos.csv: included studies by priority, access route and PDF file name."""
    import unicodedata
    rows = list(csv.DictReader(open(BRUTOS.parent / "candidatos.csv", encoding="utf-8-sig")))
    inc = [r for r in rows if r["decision"] in ("include", "include_model")]

    def nome(r):
        a = unicodedata.normalize("NFKD", (r["first_author"] or "anon").split()[-1]).encode("ascii", "ignore").decode()
        a = re.sub(r"[^A-Za-z]", "", a) or "anon"
        tail = re.sub(r"[^A-Za-z0-9]+", "-", r["doi"])[-40:] if r["doi"] else re.sub(r"[^a-z0-9]+", "-", r["title"].lower())[:40]
        return f"{a}{r['year']}_{tail}.pdf"

    order = {"high": 0, "medium": 1, "low": 2}
    inc.sort(key=lambda r: (order.get(r["pr"], 3), r["year"]))
    cols = ["prioridade", "arquivo_pdf", "acesso", "link", "doi", "ano", "primeiro_autor", "titulo", "revista",
            "decisao", "escala", "phi", "S", "n", "onde", "observacao"]
    with open(BRUTOS.parent.parent / "dados_S_phi" / "textos_completos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in inc:
            acc = "aberto" if r["oa_url"] else ("sem DOI (literatura cinza/tese)" if not r["doi"] else "Portal CAPES")
            link = r["oa_url"] or (("https://doi.org/" + r["doi"]) if r["doi"] else "")
            w.writerow([r["pr"], nome(r), acc, link, r["doi"], r["year"], r["first_author"], r["title"], r["venue"],
                        r["decision"], r["scale"], r["phi"], r["S"], r["n"], r["where"], r["manual"]])
    print(f"{len(inc)} included studies listed")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "refazer-s3":
        refazer_s3()
    elif cmd == "lotes1":
        lotes1()
    elif cmd == "lotes2":
        lotes2(sys.argv[2])
    elif cmd == "pendentes":
        pendentes()
    elif cmd == "lotes2-pendentes":
        lotes2_pendentes(sys.argv[2])
    elif cmd == "lotes1-pendentes":
        lotes1_pendentes()
    elif cmd == "scopus":
        scopus()
    elif cmd == "csv":
        escrever_csv()
        textos()
    else:
        juntar(sys.argv[2])
