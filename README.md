# Evaporation suppression by partial floating covers (MAISSER-PE): review data and code, with the search log, screening decisions, extracted S-phi conditions, synthesis and meta-regression

**DOI:** assigned by Zenodo at the first release (see CITATION.cff after the release).

Data and code of the review *Why floating covers save less water than they cover: a critical review of
the physics of evaporation from partially covered water surfaces, from gaps to reservoirs* (Cardoso et al.,
in preparation for the Journal of Hydrology), project MAISSER-PE, Departamento de Energia Nuclear,
Universidade Federal de Pernambuco, Recife, Brazil.

The review defines the suppression as S = 1 − E_c/E_o, with E_c and E_o the evaporation of the covered
and the open water body over the whole water surface, and the covered fraction as φ. It asks why S rarely
equals φ and synthesises the ratio S/φ measured or modelled under each cover.

## Layout

| Folder | Contents |
|---|---|
| `busca/` | Search protocol (`PROTOCOLO.md`, in Portuguese), search and screening code, `candidatos.csv` (every record with its screening decision and reason) |
| `busca/brutos/` | Output of each search stratum (S1–S7), log of every query (`registro_consultas.jsonl`), screening decisions of stages 1 and 2, manual adjustments (duplicates, same-author records) |
| `dados_S_phi/` | Full texts sought (`textos_completos.csv`), download log, names of the 85 retrieved full texts (`textos_obtidos.txt`), extracted conditions (`S_phi.csv`, `extracao.json`), study-level decisions (`estudos_extraidos.csv`), corrections of the checking pass (`mudancas_verificacao.csv`), assumed reduction factors (`fatores_supostos.json`), grouping of linked reports and the synthesis dataset (`S_phi_sintese.csv`) |
| `dados_S_phi/conciliacao/` | Reconciliation of linked reports of the same experiment and the pseudo-replication audit |
| `analise/` | Synthesis (`dados_sintese.py`), numbers quoted in the text (`numeros.py` → `numeros_sintese.json`), meta-regression (`metaregressao.py` → `tabelas/`), figure scripts and `figuras/` (PDF, PNG and the CSV behind each figure) |
| `_estilo_figuras/` | Figure style package (Source Sans 3 fonts under the SIL Open Font License) |

## Main numbers

The synthesis holds 326 conditions from 47 studies (one report per experiment), of which
269 conditions from 40 studies are measurements. The median measured S/φ is
0.74, and 88% of the measured conditions have S/φ below 1. Every number
quoted in the review text is in `analise/numeros_sintese.json`.

## Reproducing the synthesis, the meta-regression and the figures

```
pip install -r requirements.txt
pip install -e _estilo_figuras
cd analise
python -X utf8 numeros.py
python -X utf8 metaregressao.py
python -X utf8 fig01_prisma.py        # and the other fig*.py scripts
```

The search (`busca/busca_api.py`, `consolidar_busca.py`) and the retrieval of full texts
(`baixar_textos.py`) need API keys (OpenAlex; Elsevier for Scopus; Wiley TDM) in the environment
variables `OPENALEX_API_KEY`, `ELSEVIER_API_KEY` and `WILEY_TDM_TOKEN` or in `~/.openalex_key`, `~/.elsevier_key` and
`~/.wiley_tdm_token`. No key is included in this repository. The extraction support
(`preparar_extracao.py`) needs the full texts themselves.

## What is not included, and why

The full texts of the reviewed publications, any verbatim passages taken from them, their abstracts and
the raw Scopus records are not redistributed (copyright and database licences). Each record keeps its DOI
or title, so every full text can be obtained from its publisher. Extracted values carry a short locator
(page, table or figure) to the source.

## Licence and citation

Code: MIT (`LICENSE`). Data, figures and documentation: CC BY 4.0 (`LICENSE-data.txt`). Please cite this
deposit (see `CITATION.cff`). The data and code of the companion modelling studies (MAISSER-PE evaporation
pan) are at doi:10.5281/zenodo.23787708.
