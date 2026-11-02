"""Downloads the open-access full texts listed in dados_S_phi/textos_completos.csv into textos/.

    python -I -X utf8 baixar_textos.py             # rows with acesso == aberto (files already there are kept)
    python -I -X utf8 baixar_textos.py --capes     # also the Portal CAPES rows, through any OA copy OpenAlex knows
    python -I -X utf8 baixar_textos.py --cinza     # only the records without DOI, found by title (OpenAlex, S2)
    python -I -X utf8 baixar_textos.py lista       # textos/BAIXAR_MANUALMENTE.html with the studies still missing
    python -I -X utf8 baixar_textos.py organizar   # files PDFs saved by hand in textos/_entrada/ (match by DOI/title)

Rerunning retries only the studies without a PDF yet.

For each study the candidate URLs are the pdf_url of every OpenAlex location, the listed link and the
PDF links announced by landing pages (citation_pdf_url meta tag, application/pdf link, DSpace
bitstreams, MDPI /pdf). The first response that is a real PDF (%PDF header) is kept and checked
against the title. Everything is logged in dados_S_phi/registro_downloads.csv. Sites that answer
with a challenge or 403 are recorded as blocked and left for manual download; nothing is bypassed.

Subscription content: from the university network, the text-and-data-mining routes of Elsevier
(API key in ~/.elsevier_key) and Wiley (TDM token in ~/.wiley_tdm_token) are tried first when the
credentials exist; the publisher decides access from the institution's IP. Requests to each site
are spaced (8 s; 11 s for the Wiley API) and a site that refuses three times is skipped for the
rest of the run, so that the downloads never look like bulk harvesting.

Standalone (no import of busca_api) so that it can run with python -I. The keys are read from
environment variables or files in the home folder and never printed.
"""
import csv
import hashlib
import html
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

import pymupdf
import requests

RAIZ = Path(__file__).resolve().parent.parent
LISTA = RAIZ / "dados_S_phi" / "textos_completos.csv"
REGISTRO = RAIZ / "dados_S_phi" / "registro_downloads.csv"
PASTA = RAIZ / "textos"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) maisser-cover-review/1.0"
MAX_BYTES = 80 * 2**20
MAX_TENTATIVAS = 10


def chave(env, arquivo):
    """Key from the environment, then ~/<arquivo>, then the key folder on the external drive."""
    k = os.environ.get(env)
    for p in (Path.home() / arquivo, Path("D:/CHAVES_API") / (arquivo.lstrip(".") + ".txt")):
        if not k and p.exists():
            k = p.read_text().strip()
    return k or ""


def oa_key():
    return chave("OPENALEX_API_KEY", ".openalex_key")


# Publisher text-and-data-mining routes, used only when the user has put the credentials in place.
# Access to subscription content is decided by the publisher from the institution's IP address.
ELSEVIER = chave("ELSEVIER_API_KEY", ".elsevier_key")
WILEY = chave("WILEY_TDM_TOKEN", ".wiley_tdm_token")
CABECALHOS = {"api.elsevier.com": {"X-ELS-APIKey": ELSEVIER, "Accept": "application/pdf"},
              "api.wiley.com": {"Wiley-TDM-Client-Token": WILEY}}


def tdm(doi):
    """Text-mining URLs of Elsevier and Wiley for a DOI, when their credentials exist."""
    d = doi.lower()
    if ELSEVIER and d.startswith("10.1016/"):
        return [f"https://api.elsevier.com/content/article/doi/{doi}?httpAccept=application/pdf"]
    if WILEY and d.startswith(("10.1002/", "10.1029/", "10.1111/")):
        return ["https://api.wiley.com/onlinelibrary/tdm/v1/articles/" + urllib.parse.quote(doi, safe="")]
    return []


def locais(dois):
    """doi -> list of (pdf_url, landing_page_url), best OA location first."""
    out = {}
    s = requests.Session()
    for k in range(0, len(dois), 50):
        q = {"filter": "doi:" + "|".join(dois[k:k + 50]), "per-page": 50,
             "select": "doi,best_oa_location,locations", "api_key": oa_key()}
        r = s.get("https://api.openalex.org/works", params=q, timeout=60)
        r.raise_for_status()
        for w in r.json().get("results", []):
            d = (w.get("doi") or "").lower().replace("https://doi.org/", "")
            locs = [w.get("best_oa_location") or {}] + (w.get("locations") or [])
            out[d] = [(l.get("pdf_url"), l.get("landing_page_url")) for l in locs if l]
        time.sleep(0.3)
    return out


def links_da_pagina(url, texto):
    """PDF links announced by a landing page."""
    achados = []
    for pat in (r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url',
                r'<link[^>]+type=["\']application/pdf["\'][^>]+href=["\']([^"\']+)',
                r'href=["\']([^"\']*/bitstream/[^"\']+\.pdf[^"\']*)'):
        achados += re.findall(pat, texto, flags=re.I)
    if "mdpi.com" in url and not url.rstrip("/").endswith("/pdf"):
        achados.append(url.rstrip("/") + "/pdf")
    return [urllib.parse.urljoin(url, html.unescape(a)) for a in achados]


def dspace7(s, url):
    """PDF files of a DSpace 7 item page (an Angular shell with no links) through the repository's REST API."""
    m = re.match(r"(https?://[^/]+)(?:/[^/?#]+)*?/handle/(\d+(?:\.\d+)*/\d+)", url)
    if not m:
        return []
    try:
        it = s.get(m.group(1) + "/server/api/pid/find", params={"id": "hdl:" + m.group(2)}, timeout=60).json()
        bl = s.get(it["_links"]["bundles"]["href"], params={"embed": "bitstreams"}, timeout=60).json()
    except (requests.RequestException, ValueError, KeyError):
        return []
    out = []
    for bd in bl.get("_embedded", {}).get("bundles", []):
        if bd.get("name") == "ORIGINAL":
            for bs in bd.get("_embedded", {}).get("bitstreams", {}).get("_embedded", {}).get("bitstreams", []):
                if bs.get("name", "").lower().endswith(".pdf"):
                    out.append((bs.get("sizeBytes") or 0, bs["_links"]["content"]["href"]))
    return [u for _, u in sorted(out, reverse=True)]          # the full document before abstracts


def palavras(t):
    t = unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()
    return {w for w in re.findall(r"[a-z]{4,}", t)}


def confere(caminho, titulo):
    """(pages, share of title words found on the first two pages)."""
    with pymupdf.open(caminho) as doc:
        txt = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        n = doc.page_count
    tw = palavras(titulo)
    txt = re.sub(r"-\s*\n\s*", "", txt)
    return n, (len(tw & palavras(txt)) / len(tw) if tw else 0.0)


ULTIMO, RECUSAS = {}, {}     # per-site politeness: last request time, refusals in this run
INTERVALO = 8.0              # seconds between requests to the same site (subscription publishers watch bulk downloads)
INTERVALO_SITE = {"api.wiley.com": 11.0}   # Wiley TDM allows 60 requests per 10 minutes
MAX_RECUSAS = 3              # after this many refusals a site is skipped for the rest of the run


def site(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def baixar(s, row, cand):
    """Tries the candidate URLs in order; returns (status, url, bytes, sha, pages, match)."""
    destino = PASTA / row["arquivo_pdf"]
    vistos, fila, status = set(), list(cand), "sem_pdf"
    while fila and len(vistos) < MAX_TENTATIVAS:
        url = fila.pop(0)
        if not url or url in vistos:
            continue
        vistos.add(url)
        h = site(url)
        if RECUSAS.get(h, 0) >= MAX_RECUSAS:
            status = "site_recusa"
            continue
        espera = INTERVALO_SITE.get(h, INTERVALO) - (time.time() - ULTIMO.get(h, 0))
        if espera > 0:
            time.sleep(espera)
        ULTIMO[h] = time.time()
        try:
            r = s.get(url, timeout=(10, 45), stream=True, allow_redirects=True, headers=CABECALHOS.get(h))
        except requests.RequestException:
            status = "erro_rede"
            continue
        if r.status_code in (401, 403, 429) or r.status_code >= 500:
            status = f"bloqueado_{r.status_code}"
            if r.status_code in (401, 403, 429):
                RECUSAS[site(r.url)] = RECUSAS.get(site(r.url), 0) + 1
            r.close()
            continue
        if r.status_code != 200:
            r.close()
            continue
        corpo = b""
        for bloco in r.iter_content(2**16):
            corpo += bloco
            if len(corpo) > MAX_BYTES:
                break
        r.close()
        if corpo[:1024].lstrip().startswith(b"%PDF"):
            tmp = destino.with_suffix(".part")
            tmp.write_bytes(corpo)
            try:
                n, m = confere(tmp, row["titulo"])
            except Exception:
                tmp.unlink()
                status = "pdf_ilegivel"
                continue
            if h == "api.elsevier.com" and n <= 1:       # not entitled: Elsevier returns only the first page
                tmp.unlink()
                status = "so_primeira_pagina"
                continue
            tmp.replace(destino)
            return "ok" if m >= 0.5 else "ok_titulo_duvidoso", r.url.split("?")[0], len(corpo), \
                hashlib.sha256(corpo).hexdigest()[:16], n, round(m, 2)
        if b"<html" in corpo[:4096].lower() or "html" in r.headers.get("content-type", ""):
            texto = corpo[:3 * 2**20].decode("utf-8", "ignore")
            if re.search(r"captcha|cf-chl|challenge-platform|are you a robot|client challenge|just a moment",
                         texto, re.I):
                status = "bloqueado_desafio"
                RECUSAS[site(r.url)] = RECUSAS.get(site(r.url), 0) + 1
                continue
            fila += [u for u in links_da_pagina(r.url, texto) + dspace7(s, r.url) if u not in vistos]
            status = "so_pagina"
        time.sleep(0.5)
    return status, "", 0, "", 0, 0.0


def escrever(linhas):
    cols = ["arquivo", "prioridade", "acesso", "doi", "status", "url", "bytes", "sha256_16", "paginas",
            "titulo_no_pdf", "titulo"]
    with open(REGISTRO, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(linhas)


def outras_fontes(s, doi):
    """PDF links from Europe PMC and Semantic Scholar, which allow programmatic access."""
    urls = []
    try:
        r = s.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                  params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"}, timeout=30)
        for res in r.json().get("resultList", {}).get("result", []):
            for f in (res.get("fullTextUrlList") or {}).get("fullTextUrl", []):
                if f.get("documentStyle") == "pdf" and f.get("availabilityCode") in ("OA", "F"):
                    urls.append(f["url"])
            if res.get("pmcid") and res.get("isOpenAccess") == "Y":
                urls.append(f"https://europepmc.org/articles/{res['pmcid']}?pdf=render")
    except (requests.RequestException, ValueError):
        pass
    try:
        r = s.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                  params={"fields": "openAccessPdf"}, timeout=30)
        if r.ok:
            u = (r.json().get("openAccessPdf") or {}).get("url")
            if u:
                urls.append(u)
    except (requests.RequestException, ValueError):
        pass
    return urls


def por_titulo(s, titulo, ano):
    """Candidate URLs for a record without DOI: OpenAlex title search and Semantic Scholar title match."""
    limpo = re.sub(r"\([^)]*\)", " ", titulo)
    limpo = " ".join(re.sub(r"[^\w\s-]", " ", limpo).split()[:14])
    alvo, urls = palavras(limpo), []

    def parecido(t, a):
        p = palavras(t)
        j = len(alvo & p) / max(len(alvo | p), 1)
        return j >= 0.6 and (not ano or not a or abs(int(a) - int(ano)) <= 2)

    try:
        r = s.get("https://api.openalex.org/works", timeout=30,
                  params={"filter": "title.search:" + limpo, "per-page": 5, "api_key": oa_key(),
                          "select": "display_name,publication_year,best_oa_location,locations"})
        for w in r.json().get("results", []):
            if parecido(w.get("display_name") or "", w.get("publication_year")):
                locs = [w.get("best_oa_location") or {}] + (w.get("locations") or [])
                urls += [l.get("pdf_url") for l in locs if l and l.get("pdf_url")]
                urls += [l.get("landing_page_url") for l in locs if l and l.get("landing_page_url")]
    except (requests.RequestException, ValueError):
        pass
    try:
        r = s.get("https://api.semanticscholar.org/graph/v1/paper/search/match", timeout=30,
                  params={"query": limpo, "fields": "title,year,openAccessPdf"})
        if r.ok:
            for p in r.json().get("data", []):
                u = (p.get("openAccessPdf") or {}).get("url")
                if u and parecido(p.get("title") or "", p.get("year")):
                    urls.append(u)
    except (requests.RequestException, ValueError):
        pass
    return list(dict.fromkeys(u for u in urls if u))


def organizar():
    """Files the PDFs saved by hand in textos/_entrada/ under their listed names (match by DOI, then title)."""
    rows = list(csv.DictReader(open(LISTA, encoding="utf-8-sig")))
    por_doi = {r["doi"].lower(): r for r in rows if r["doi"]}
    antigo = {}
    if REGISTRO.exists():
        antigo = {r["arquivo"]: r for r in csv.DictReader(open(REGISTRO, encoding="utf-8-sig"))}
    for pdf in sorted((PASTA / "_entrada").glob("*.pdf")):
        try:
            with pymupdf.open(pdf) as doc:
                txt = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        except Exception:
            print("ilegível:", pdf.name)
            continue
        alvo = None
        for d in re.findall(r"10\.\d{4,9}/[^\s\"<>]+", txt):
            d = d.rstrip(".,;)").lower()
            if d in por_doi:
                alvo = por_doi[d]
                break
        if not alvo:
            pw = palavras(re.sub(r"-\s*\n\s*", "", txt))
            nota = [(len(palavras(r["titulo"]) & pw) / max(len(palavras(r["titulo"])), 1), r) for r in rows]
            m, r = max(nota, key=lambda x: x[0])
            alvo = r if m >= 0.8 else None
        if not alvo:
            print("sem correspondência:", pdf.name)
            continue
        destino = PASTA / alvo["arquivo_pdf"]
        if destino.exists():
            print("já existe:", destino.name, "<-", pdf.name)
            continue
        pdf.replace(destino)
        n, m = confere(destino, alvo["titulo"])
        corpo = destino.read_bytes()
        antigo[destino.name] = {"arquivo": destino.name, "prioridade": alvo["prioridade"], "acesso": alvo["acesso"],
                                "doi": alvo["doi"], "status": "ok_manual", "url": "", "bytes": len(corpo),
                                "sha256_16": hashlib.sha256(corpo).hexdigest()[:16], "paginas": n,
                                "titulo_no_pdf": round(m, 2), "titulo": alvo["titulo"]}
        print(f"{pdf.name} -> {destino.name}")
    escrever(list(antigo.values()))


def lista():
    """textos/BAIXAR_MANUALMENTE.html: studies with a DOI still without a PDF, by priority and access route."""
    rows = list(csv.DictReader(open(LISTA, encoding="utf-8-sig")))
    falta = [r for r in rows if not (PASTA / r["arquivo_pdf"]).exists()]
    ordem = {"high": 0, "medium": 1, "low": 2}
    falta.sort(key=lambda r: (ordem.get(r["prioridade"], 3), r["ano"]))
    linhas = []
    for grupo, titulo in (("aberto", "Acesso aberto (o site recusou o download automático)"),
                          ("Portal CAPES", "Portal CAPES (entrar pela rede da UFPE ou pelo login CAFe)"),
                          ("sem DOI", "Sem DOI: teses, relatórios e literatura cinza (o link abre uma busca "
                                      "no Google Acadêmico; procure o PDF no repositório indicado)")):
        g = [r for r in falta if r["acesso"].startswith(grupo)]
        linhas.append(f"<h2>{titulo}: {len(g)}</h2><ol>")
        for r in g:
            if r["doi"]:
                href = "https://doi.org/" + r["doi"]
            else:
                q = re.sub(r"\([^)]*\)", " ", r["titulo"])
                href = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(" ".join(q.split()))
            linhas.append(f'<li><b>[{r["prioridade"]}]</b> <a href="{html.escape(href)}" '
                          f'target="_blank">{html.escape(r["titulo"])}</a> — {html.escape(r["primeiro_autor"])} '
                          f'({r["ano"]}), <i>{html.escape(r["revista"])}</i></li>')
        linhas.append("</ol>")
    (PASTA / "_entrada").mkdir(exist_ok=True)
    (PASTA / "BAIXAR_MANUALMENTE.html").write_text(
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>PDFs a baixar</title>"
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}"
        "li{margin:.3rem 0}</style><h1>Textos completos que faltam (Artigo 3)</h1>"
        "<p>Abra cada link, baixe o PDF e salve na pasta <code>textos/_entrada/</code> com qualquer nome. "
        "Depois rode <code>python -I -X utf8 busca/baixar_textos.py organizar</code> (ou peça ao Claude): "
        "o script reconhece cada PDF pelo DOI ou pelo título e o renomeia.</p>" + "".join(linhas),
        encoding="utf-8")
    print(f"{len(falta)} studies listed in textos/BAIXAR_MANUALMENTE.html")


def main():
    if "organizar" in sys.argv:
        return organizar()
    if "lista" in sys.argv:
        return lista()
    capes, cinza = "--capes" in sys.argv, "--cinza" in sys.argv
    PASTA.mkdir(exist_ok=True)
    rows = list(csv.DictReader(open(LISTA, encoding="utf-8-sig")))
    if cinza:
        alvo = [r for r in rows if not r["doi"]]
    else:
        alvo = [r for r in rows if r["acesso"] == "aberto" or (capes and r["acesso"] == "Portal CAPES")]
    loc = locais([r["doi"].lower() for r in alvo if r["doi"]])
    antigo = {}
    if REGISTRO.exists():
        antigo = {r["arquivo"]: r for r in csv.DictReader(open(REGISTRO, encoding="utf-8-sig"))}
    s = requests.Session()
    s.headers.update({"User-Agent": UA})        # an explicit Accept with text/html makes MDPI serve a stub page
    saida = []
    for i, r in enumerate(alvo, 1):
        arq = r["arquivo_pdf"]
        if (PASTA / arq).exists() and arq in antigo and antigo[arq]["status"].startswith("ok"):
            saida.append(antigo[arq])
            continue
        pares = loc.get(r["doi"].lower(), [])
        cand = tdm(r["doi"]) + [p for p, _ in pares if p] + [r["link"]]
        if r["doi"]:
            cand += outras_fontes(s, r["doi"])
        else:
            cand += por_titulo(s, r["titulo"], r["ano"])
        cand += [l for _, l in pares if l]
        if r["doi"]:
            cand.append("https://doi.org/" + r["doi"])
        st, url, nb, sha, pag, m = baixar(s, r, cand)
        print(f"[{i}/{len(alvo)}] {st:20s} {arq}", flush=True)
        saida.append({"arquivo": arq, "prioridade": r["prioridade"], "acesso": r["acesso"], "doi": r["doi"],
                      "status": st, "url": url, "bytes": nb, "sha256_16": sha, "paginas": pag,
                      "titulo_no_pdf": m, "titulo": r["titulo"]})
        escrever(saida + [v for k, v in antigo.items() if k not in {x["arquivo"] for x in saida}])
    from collections import Counter
    print(Counter(x["status"] for x in saida))


if __name__ == "__main__":
    main()
