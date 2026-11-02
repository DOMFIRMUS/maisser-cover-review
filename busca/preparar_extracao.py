"""Turns the downloaded PDFs into page-tagged text and builds the S/phi extraction batches.

    python -I -X utf8 preparar_extracao.py texto                 # textos/*.pdf -> dados_S_phi/textos_txt/*.txt
    python -I -X utf8 preparar_extracao.py lotes high,medium     # evidence packs -> dados_S_phi/lotes_extracao/

Each study in a batch carries its metadata, the screening notes and an evidence pack: the whole
text without the reference list when it is short, otherwise the first page plus the paragraphs,
tables and captions that mention evaporation, covers or numbers, up to CAP characters. The
extractor can open the full text (textos_txt/) or the PDF itself (for scanned pages) when the pack
is not enough. Standalone so that it can run with python -I (the PDFs are untrusted input).
"""
import csv
import re
import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PDFS = RAIZ / "textos"
TXT = RAIZ / "dados_S_phi" / "textos_txt"
LOTES = RAIZ / "dados_S_phi" / "lotes_extracao"
CAP = 26000            # characters of evidence per study
LOTE_MAX = 100000      # characters per batch file
FIM = re.compile(r"^\s*(references|reference list|bibliography|literature cited|works cited|"
                 r"refer[eê]ncias( bibliogr[aá]ficas)?|referencias( bibliogr[aá]ficas)?|bibliograf[ií]a)\s*$", re.I)
CHAVE = re.compile(r"evapor|cover|shade|suppress|reduc|saving|saved|loss|coverage|fraction|floating|"
                   r"ball|disc|hexag|module|raft|panel|array|wind|gap|pan\b|tank|reservoir|pond|dam\b|"
                   r"mm\s*(d|day|h|month|yr)|mm/|m3|%|φ|ϕ|control|uncovered|open water|table|fig", re.I)


def texto():
    TXT.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(PDFS.glob("*.pdf")):
        dest = TXT / (pdf.stem + ".txt")
        if dest.exists() and dest.stat().st_mtime >= pdf.stat().st_mtime:
            continue
        try:
            with pymupdf.open(pdf) as doc:
                paginas = [doc[i].get_text("blocks") for i in range(doc.page_count)]
        except Exception as e:
            print("ilegível:", pdf.name, e)
            continue
        linhas = []
        for i, blocos in enumerate(paginas, 1):
            linhas.append(f"[p. {i}]")
            for b in blocos:
                if b[6] == 0:                       # text block
                    t = re.sub(r"-\s*\n\s*(?=[a-z])", "", b[4]).replace("\n", " ")
                    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f�]", " ", t).strip()   # control bytes from bad fonts
                    if t:
                        linhas.append(t)
        dest.write_text("\n".join(linhas), encoding="utf-8")
        n = sum(len(x) for x in linhas)
        print(f"{pdf.stem}: {len(paginas)} p., {n} chars" + ("  (pouco texto: escaneado?)" if n < 400 * len(paginas) else ""))


def corta_referencias(linhas):
    """Drops everything after the last reference-list heading in the second half."""
    for k in range(len(linhas) - 1, len(linhas) // 2, -1):
        if FIM.match(linhas[k]):
            return linhas[:k]
    return linhas


def pacote(linhas):
    linhas = corta_referencias(linhas)
    inteiro = "\n".join(linhas)
    if len(inteiro) <= CAP:
        return inteiro, False
    # first page (title, abstract) always; then the most relevant passages (consecutive lines of one
    # page merged to ~900 characters, so that line-per-block PDFs keep their context), in reading order
    p2 = next((k for k, l in enumerate(linhas) if l == "[p. 2]"), min(len(linhas), 40))
    cabeca = linhas[:p2]
    trechos, pag, atual = [], "", []
    for l in linhas[p2:] + ["[p. fim]"]:
        nova = re.match(r"\[p\. (\d+|fim)\]$", l)
        if atual and (nova or sum(len(x) for x in atual) >= 900):
            trechos.append((pag, " ".join(atual)))
            atual = []
        if nova:
            pag = l
        elif not re.search(r"\.{4,}|…{2,}", l):          # skip table-of-contents lines
            atual.append(l)

    def nota(t):
        s = len(CHAVE.findall(t)) + 0.5 * len(re.findall(r"\d+(?:[.,]\d+)?", t))
        s += 6 * len(re.findall(r"\b(table|tab\.|fig\.?|figure|tabela|figura|tabla)\s*\d", t, re.I))
        if re.search(r"evapor", t, re.I) and re.search(r"%|percent|por ?ciento", t, re.I) and \
                re.search(r"reduc|redu[cç][aã]o|suppress|sav|ahorr|economi|efficien|eficien", t, re.I):
            s += 15                           # the study's own result statements
        return s / (1 + len(t) / 900)

    orc = CAP - sum(len(l) for l in cabeca)
    escolhidos = set()
    for k in sorted(range(len(trechos)), key=lambda k: -nota(trechos[k][1])):
        if orc <= 0 or nota(trechos[k][1]) <= 0:
            break
        escolhidos.add(k)
        orc -= len(trechos[k][1]) + 1
    out, ultima_pag, ultimo = list(cabeca), None, -2
    for k, (pg, t) in enumerate(trechos):
        if k in escolhidos:
            if k != ultimo + 1:
                out.append("[...]")
            if pg != ultima_pag:
                out.append(pg)
                ultima_pag = pg
            out.append(t)
            ultimo = k
    return "\n".join(out), True


def lotes(prioridades):
    meta = {r["arquivo_pdf"][:-4]: r for r in csv.DictReader(open(RAIZ / "dados_S_phi" / "textos_completos.csv",
                                                                     encoding="utf-8-sig"))}
    LOTES.mkdir(parents=True, exist_ok=True)
    feitos, k0 = set(), 0                 # studies already in a batch keep it; new batches continue the numbering
    for f in LOTES.glob("lote_*.md"):
        feitos |= set(re.findall(r"^## STUDY (\S+)", f.read_text(encoding="utf-8"), flags=re.M))
        k0 = max(k0, int(f.stem[5:]))
    ordem = {"high": 0, "medium": 1, "low": 2}
    estudos = sorted((s for s in meta if (TXT / (s + ".txt")).exists() and meta[s]["prioridade"] in prioridades
                      and s not in feitos),
                     key=lambda s: (ordem.get(meta[s]["prioridade"], 3), meta[s]["ano"]))
    blocos = []
    for s in estudos:
        m = meta[s]
        linhas = (TXT / (s + ".txt")).read_text(encoding="utf-8").split("\n")
        corpo, cortado = pacote(linhas)
        npag = sum(1 for l in linhas if re.match(r"\[p\. \d+\]$", l))
        escaneado = len("".join(linhas)) < 400 * max(npag, 1)
        cab = (f"## STUDY {s}\n"
               f"- doi: {m['doi'] or '-'} | year: {m['ano']} | first author: {m['primeiro_autor']} | venue: {m['revista']}\n"
               f"- title: {m['titulo']}\n"
               f"- screening (from abstract): decision {m['decisao']}; scale {m['escala'] or '-'}; phi {m['phi'] or '-'}; "
               f"S {m['S'] or '-'}; conditions {m['n'] or '-'}; values in {m['onde'] or '-'}"
               + (f"; note: {m['observacao']}" if m['observacao'] else "") + "\n"
               f"- full text: dados_S_phi/textos_txt/{s}.txt ({npag} pages)"
               + (" — EVIDENCE PACK ONLY, open the full text for anything missing" if cortado else "")
               + (f"; PDF textos/{s}.pdf looks SCANNED (little text): read its pages with the Read tool" if escaneado else "")
               + "\n\n")
        blocos.append(cab + corpo + "\n\n")
    n, atual, k = 0, "", k0
    for b in blocos:
        if atual and len(atual) + len(b) > LOTE_MAX:
            k += 1
            (LOTES / f"lote_{k:02d}.md").write_text(atual, encoding="utf-8")
            atual = ""
        atual += b
        n += 1
    if atual:
        k += 1
        (LOTES / f"lote_{k:02d}.md").write_text(atual, encoding="utf-8")
    print(f"{n} studies in batches {k0 + 1}-{k} -> {LOTES}")


if __name__ == "__main__":
    if sys.argv[1] == "texto":
        texto()
    elif sys.argv[1] == "lotes":
        lotes(set(sys.argv[2].split(",")) if len(sys.argv) > 2 else {"high", "medium", "low"})
