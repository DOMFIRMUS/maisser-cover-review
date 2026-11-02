"""Compact literature-search client for the review (OpenAlex, Crossref, Semantic Scholar).

Prints one line per record and appends every query to brutos/registro_consultas.jsonl, so the
search log of the review method is written by the tool, not reconstructed afterwards.

    python -X utf8 busca_api.py oa "floating balls evaporation" --tag S1 --id OA1
    python -X utf8 busca_api.py oa-cites W2001234567 --tag S1 --id OA2        # forward chaining
    python -X utf8 busca_api.py oa-refs 10.1029/2010WR009889 --tag S1 --id OA3  # backward chaining
    python -X utf8 busca_api.py oa-get 10.1029/2010WR009889 10.5194/hess-22-4015-2018 --abs
    python -X utf8 busca_api.py cr "shade cloth reservoir evaporation" --tag S2 --id CR1
    python -X utf8 busca_api.py s2 "floating photovoltaic evaporation" --tag S3 --id SS1 --abs
    python -X utf8 busca_api.py s2-cites 10.1029/2010WR009889 --tag S1 --id SS2

The OpenAlex key is read from OPENALEX_API_KEY or ~/.openalex_key and never printed or logged.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOG = Path(__file__).resolve().parent / "brutos" / "registro_consultas.jsonl"
UA = {"User-Agent": "maisser-cover-review/1.0"}
OA_SELECT = ("id,doi,display_name,publication_year,authorships,primary_location,type,"
             "cited_by_count,open_access,best_oa_location")


def chave(env, arquivo):
    """Key from the environment, then ~/<arquivo>, then the key folder on the external drive."""
    k = os.environ.get(env)
    for p in (Path.home() / arquivo, Path("D:/CHAVES_API") / (arquivo.lstrip(".") + ".txt")):
        if not k and p.exists():
            k = p.read_text().strip()
    return k or ""


def oa_key():
    return chave("OPENALEX_API_KEY", ".openalex_key")


def els_key():
    return chave("ELSEVIER_API_KEY", ".elsevier_key")


def get(url, params=None, key=None, headers=None):
    q = dict(params or {})
    if key:
        q["api_key"] = key
    full = url + ("?" + urllib.parse.urlencode(q, safe=":|,") if q else "")
    for wait in (0, 5, 15, 40):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(full, headers={**UA, **(headers or {})}),
                                        timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
    sys.exit(f"falhou após tentativas: {url}")   # the URL never carries a key in clear: OpenAlex key is a parameter only when set, Scopus uses a header


def log(a, source, query, hits, returned):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "tag": a.tag, "id": a.id,
           "source": source, "cmd": a.cmd, "query": query, "hits": hits, "returned": returned}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def bare(doi):
    d = (doi or "").strip()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if d.lower().startswith(p):
            d = d[len(p):]
    return d


def abstract_of(inv):
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def show(i, wid, doi, year, author, venue, title, cites, oa="", abst="", nabs=500):
    line = f"[{i}] {wid} | {doi or '-'} | {year or '?'} | {author or '?'} | {(venue or '-')[:40]} | {title} | cit {cites}"
    if oa:
        line += f" | OA {oa}"
    print(line)
    if abst:
        print("     abs: " + abst[:nabs].replace("\n", " "))


def oa_print(works, a):
    for i, w in enumerate(works, 1):
        au = w.get("authorships") or []
        first = au[0]["author"]["display_name"] if au else ""
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        oa = (w.get("best_oa_location") or {}).get("pdf_url") or (w.get("best_oa_location") or {}).get("landing_page_url") or ""
        show(i, w["id"].rsplit("/", 1)[-1], bare(w.get("doi")), w.get("publication_year"), first, venue,
             w.get("display_name"), w.get("cited_by_count"), oa if (w.get("open_access") or {}).get("is_oa") else "",
             abstract_of(w.get("abstract_inverted_index")) if a.abs else "", a.abs_chars)


def oa_list(filt, a, label):
    sel = OA_SELECT + (",abstract_inverted_index" if a.abs else "")
    d = get("https://api.openalex.org/works", {"filter": filt, "per-page": a.n, "select": sel}, oa_key())
    res = d.get("results", [])
    print(f"# OpenAlex {label}: {d['meta']['count']} hits, {len(res)} shown")
    oa_print(res, a)
    log(a, "OpenAlex", label, d["meta"]["count"], len(res))


def oa_ids(ids, a):
    """Resolve DOIs or W ids in batches of 50."""
    dois = [bare(x) for x in ids if not x.upper().startswith("W")]
    ws = [x for x in ids if x.upper().startswith("W")]
    out = []
    sel = OA_SELECT + (",abstract_inverted_index" if a.abs else "")
    for field, vals in (("doi", dois), ("openalex_id", ws)):
        for k in range(0, len(vals), 50):
            d = get("https://api.openalex.org/works",
                    {"filter": f"{field}:" + "|".join(vals[k:k + 50]), "per-page": 50, "select": sel}, oa_key())
            out += d.get("results", [])
    return out


def sc_lista(query, n=100, from_year=0):
    """Scopus Search API (Elsevier key in a header). Returns {'total', 'itens'}; 25 records per page."""
    if from_year:
        query = f"({query}) AND PUBYEAR > {from_year - 1}"
    itens, total, start = [], 0, 0
    while len(itens) < n:
        d = get("https://api.elsevier.com/content/search/scopus",
                {"query": query, "count": 25, "start": start,
                 "field": "eid,dc:title,prism:doi,prism:coverDate,dc:creator,prism:publicationName,citedby-count,"
                          "openaccessFlag,subtypeDescription"},
                headers={"X-ELS-APIKey": els_key(), "Accept": "application/json"})
        r = (d or {}).get("search-results", {})
        total = int(r.get("opensearch:totalResults", 0) or 0)
        ents = [e for e in r.get("entry", []) if "error" not in e]
        if not ents:
            break
        for e in ents:
            itens.append({"eid": e.get("eid", ""), "doi": (e.get("prism:doi") or "").lower(),
                          "title": e.get("dc:title", ""), "year": (e.get("prism:coverDate") or "")[:4],
                          "first_author": e.get("dc:creator", ""), "venue": e.get("prism:publicationName", ""),
                          "cites": e.get("citedby-count", ""), "oa": e.get("openaccessFlag") in (True, "true"),
                          "type": e.get("subtypeDescription", "")})
        start += 25
        if start >= total:
            break
    return {"total": total, "itens": itens[:n]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["oa", "oa-cites", "oa-refs", "oa-get", "cr", "sc", "s2", "s2-cites", "s2-refs"])
    ap.add_argument("q", nargs="+", help="search terms, or ids/DOIs")
    ap.add_argument("--tag", default="", help="search stratum, e.g. S1")
    ap.add_argument("--id", default="", help="query id, e.g. OA3")
    ap.add_argument("--n", type=int, default=100, help="records to show (OpenAlex <=200, Crossref <=100, S2 <=100)")
    ap.add_argument("--from-year", type=int, default=0)
    ap.add_argument("--abs", action="store_true", help="print the abstract (first --abs-chars characters)")
    ap.add_argument("--abs-chars", type=int, default=500)
    a = ap.parse_args()
    terms = " ".join(a.q)

    if a.cmd == "oa":
        filt = "title_and_abstract.search:" + terms.replace(",", " ")
        if a.from_year:
            filt += f",from_publication_date:{a.from_year}-01-01"
        oa_list(filt, a, terms)
    elif a.cmd == "oa-cites":
        w = a.q[0] if a.q[0].upper().startswith("W") else oa_ids([a.q[0]], a)[0]["id"].rsplit("/", 1)[-1]
        oa_list(f"cites:{w}", a, f"cites:{a.q[0]}")
    elif a.cmd == "oa-refs":
        d = oa_ids([a.q[0]], argparse.Namespace(**{**vars(a), "abs": False}))
        if not d:
            sys.exit("não encontrado no OpenAlex")
        full = get("https://api.openalex.org/works/" + d[0]["id"].rsplit("/", 1)[-1],
                   {"select": "id,referenced_works"}, oa_key())
        refs = [r.rsplit("/", 1)[-1] for r in full.get("referenced_works", [])]
        works = oa_ids(refs, a)
        print(f"# OpenAlex referências de {a.q[0]}: {len(refs)} ids, {len(works)} resolvidas")
        oa_print(works, a)
        log(a, "OpenAlex", f"refs:{a.q[0]}", len(refs), len(works))
    elif a.cmd == "oa-get":
        works = oa_ids(a.q, a)
        print(f"# OpenAlex get: {len(a.q)} pedidos, {len(works)} encontrados")
        oa_print(works, a)
    elif a.cmd == "sc":
        res = sc_lista(terms, a.n, a.from_year)
        print(f"# Scopus {terms}: {res['total']} hits, {len(res['itens'])} shown")
        for i, it in enumerate(res["itens"], 1):
            show(i, it["eid"], it["doi"], it["year"], it["first_author"], it["venue"], it["title"], it["cites"],
                 "OA" if it["oa"] else "")
        log(a, "Scopus", terms, res["total"], len(res["itens"]))
    elif a.cmd == "cr":
        sel = "DOI,title,author,issued,container-title,type,is-referenced-by-count" + (",abstract" if a.abs else "")
        d = get("https://api.crossref.org/works", {"query.bibliographic": terms, "rows": min(a.n, 100), "select": sel})
        items = d["message"]["items"]
        print(f"# Crossref {terms}: {d['message']['total-results']} hits, {len(items)} shown")
        for i, it in enumerate(items, 1):
            au = it.get("author") or [{}]
            year = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            show(i, it.get("type", ""), it.get("DOI"), year, au[0].get("family", au[0].get("name", "")),
                 (it.get("container-title") or [""])[0], (it.get("title") or [""])[0],
                 it.get("is-referenced-by-count"), "", it.get("abstract", "") if a.abs else "", a.abs_chars)
        log(a, "Crossref", terms, d["message"]["total-results"], len(items))
    else:
        f = "title,year,externalIds,authors,venue,citationCount,openAccessPdf" + (",abstract" if a.abs else "")
        base = "https://api.semanticscholar.org/graph/v1/paper/"
        if a.cmd == "s2":
            d = get(base + "search", {"query": terms, "limit": min(a.n, 100), "fields": f})
            papers, total = d.get("data", []), d.get("total", 0)
        else:
            rel = "citations" if a.cmd == "s2-cites" else "references"
            d = get(base + "DOI:" + bare(a.q[0]) + "/" + rel, {"limit": 1000, "fields": f})
            if d is None:
                sys.exit("não encontrado no Semantic Scholar")
            k = "citingPaper" if rel == "citations" else "citedPaper"
            papers = [x[k] for x in d.get("data", []) if x.get(k, {}).get("title")]
            total = len(papers)
        print(f"# SemanticScholar {a.cmd} {terms}: {total} hits, {len(papers)} shown")
        for i, p in enumerate(papers, 1):
            au = p.get("authors") or [{}]
            show(i, "S2", (p.get("externalIds") or {}).get("DOI", ""), p.get("year"), au[0].get("name", ""),
                 p.get("venue", ""), p.get("title"), p.get("citationCount"),
                 (p.get("openAccessPdf") or {}).get("url", ""), (p.get("abstract") or "") if a.abs else "", a.abs_chars)
        log(a, "SemanticScholar", f"{a.cmd}:{terms}", total, len(papers))


if __name__ == "__main__":
    main()
