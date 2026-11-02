# Review protocol — physics of evaporation suppression by partial floating covers

Version 1, 28 Oct 2026. Framing A of `00_REVISAO_EQUACOES/PROPOSTA_ARTIGO_DE_REVISAO.md`.
Target: Journal of Hydrology, Review Article. This file becomes Section 2 (Review method).

## 1. Questions

- Q1. Why does the fractional evaporation suppression S of a floating cover differ from the
  covered area fraction φ, and which mechanisms (gap/pore diffusion under the boundary layer,
  thermal feedback of the covered water and of the elements, aerodynamic sheltering) control the
  sign and size of S − φ?
- Q2. What do published measurements say about S/φ as a function of φ, wind speed, gap length
  scale, element type, colour and system scale (pan → tank → farm dam → reservoir)?
- Q3. How is S measured or inferred, and which observation errors bias the reported values?
- Q4. How do suppression results transfer from laboratory to reservoirs, in particular to
  high-radiation, low-wind semi-arid reservoirs?

## 2. Definitions used for extraction

- E_o: evaporation of an uncovered reference surface under the same forcing (control pan,
  control reservoir, or model counterfactual), per unit total water-surface area.
- E_c: evaporation of the covered system, per unit total water-surface area (covered + open).
- S = 1 − E_c/E_o (total suppression). When a study reports only the evaporation of the open
  fraction, record it and compute S only if the open-area fraction is given.
- φ: fraction of the water surface physically occupied by cover elements (projected area).
  For suspended shade cloth, φ is the shaded fraction and the cover is flagged "suspended".
  For floating photovoltaics (FPV), φ is the fraction of the reservoir under the array, and the
  value of S refers to the reservoir unless stated otherwise.
- S/φ: suppression per unit covered fraction. S/φ = 1 is the area-proportional null
  hypothesis; S/φ > 1 means the cover also reduces evaporation from the open water (shading,
  sheltering, cooling); S/φ < 1 means the open gaps evaporate faster than an open surface or the
  elements heat the water.

## 3. Eligibility

Included (primary quantitative studies, for the S/φ dataset):

- floating or suspended covers of any material (balls, discs, hexagons, plates, rafts,
  modular covers, shade cloth, FPV arrays, perforated or porous sheets) on any water body
  (pan, tank, wind tunnel, farm dam, reservoir, lake);
- report E_c and E_o (or S) together with φ, or enough to compute them;
- measured (gravimetric, depth, water balance, eddy covariance, energy budget) or modelled
  with a stated physical model (flagged separately).

Included (context, not in the dataset): theory of evaporation from discrete pores and gaps;
energy balance and aerodynamics of covered water; reservoir evaporation models with covers;
chemical monolayers and continuous covers (as comparison); reviews.

Excluded: soil mulches and evaporation from porous media without free water (except as theory
for pore diffusion); covers on swimming pools only for heat loss with no evaporation data;
studies giving only a percentage with no description of φ or the control (kept in a separate
"insufficient" list).

## 4. Sources and search

Scopus was added on 2026-10-29 (stratum S8) through the Scopus Search API with a personal Elsevier
key: nine queries mirroring strata S1–S6 (`consolidar_busca.py`, list SCOPUS; every query logged),
all hits retrieved (1392 records, 1052 unique). Of these, 307 had already been found by the
OpenAlex strata (112 of the 257 studies then included) and 745 were new; the new records went
through the same two-stage screening. Scopus abstracts and Elsevier full texts are only served to
the university network, so records without any abstract wait in `brutos/lotes/sem_resumo.md`
until they can be screened from there. Web of Science and CNKI remain unavailable (limitation).
Sources:

- OpenAlex API (`title_and_abstract.search` with Boolean operators and phrases, plus citation
  chaining through `referenced_works` and `cites:`), queried with a personal API key.
- All API queries run through `busca/busca_api.py`, which appends each one (time, stratum,
  query id, source, string, hits, records returned) to `busca/brutos/registro_consultas.jsonl`.
- Crossref REST API (`query.bibliographic`), Semantic Scholar Graph API (search, citations,
  references), Google Scholar via web search for grey literature and theses.
- Grey literature: Australian NPSI/CRC reports (Craig, McJannet, Yao), USGS and USBR reports,
  FAO, Brazilian theses (BDTD, university repositories).
- Languages: English, Portuguese, Spanish; Chinese and Persian when an English abstract exists.
- Period: all years (historical USGS work from the 1950s is relevant).

Search strata (one search agent each):

1. Laboratory and pan experiments with floating elements.
2. Field studies on farm dams, irrigation ponds and reservoirs (non-FPV covers).
3. Floating photovoltaics and evaporation.
4. Theory: discrete-pore/gap diffusion, boundary layers, thermal and aerodynamic effects.
5. Reservoir-scale modelling with covers, monolayers/continuous covers, semi-arid reservoirs.
6. Existing reviews, grey literature and non-English studies.

Each agent records every query (source, string, date, number of hits, number screened) in
`busca/brutos/<stratum>.json`. Backward and forward citation chaining starts from seed papers
already verified in `00_REVISAO_EQUACOES/referencias/*.bib`.

## 5. Screening

Search agents label each record while searching (category, scale, quantitative yes/maybe/no).
Records are then merged by DOI and normalised title (`consolidar_busca.py`), abstracts are
fetched from OpenAlex, and metadata are checked by comparing the title with the OpenAlex record
of the DOI. Screening of the records labelled primary/model with yes/maybe runs in two stages:

1. Stage 1, title and abstract snippet: keep (K), context only (C) or drop (D); when unsure, K.
2. Stage 2, full abstract: include, include_model, insufficient, context_only or exclude, with
   the location of the S and φ values in the source.

The FPV stratum's results were lost when its agent stopped; its 14 OpenAlex queries were rerun
by script. Machine-rerun records were kept only if the title or abstract mentioned evaporation or
water saving and a water body (rule prefilter), before stage 1. Reasons for exclusion are
recorded. The flow (identified → deduplicated → screened → full text sought → included) is
reported as a PRISMA-style diagram.

At the full-text stage, 16 included records turned out to be duplicates that the title key had
missed (accented and unaccented spellings of the same title, a title in two languages, a
repository copy of a journal paper, a conference abstract of a preprint). They are marked
"duplicate" in `busca/brutos/ajustes_manuais.json`, leaving 240 included studies (194 measured,
46 modelled). Reports that share an experiment but are not identical (thesis and article, for
example) stay separate records and are linked during extraction (`same_study_as`).

## 6. Full texts and extraction (S/φ dataset)

Full texts: `busca/baixar_textos.py` tries, for each open-access study, the PDF links of every
OpenAlex location, Europe PMC and Semantic Scholar, the PDF links announced by landing pages and,
for DSpace 7 repositories, the files of the item through the repository's REST API; records
without DOI are first located by title (OpenAlex title search and Semantic Scholar title match);
a file is kept only if it is a PDF whose first pages contain the title. Sites that refuse
automated access (HTTP 403 or a browser challenge) are not bypassed: those studies, and the
subscription ones (Portal CAPES), are downloaded by hand and filed by `baixar_textos.py organizar`,
which recognises each PDF by DOI or title. Every attempt is logged in
`dados_S_phi/registro_downloads.csv`.

Extraction: `busca/preparar_extracao.py` converts each PDF to page-tagged text and builds batches
of 2–4 studies, each with its metadata, the screening notes and either the whole text without the
reference list or, for long documents, an evidence pack of the most relevant passages (the
extractor opens the full text or the PDF pages for anything missing; scanned and non-Latin-script
PDFs are read as images). A first reviewer (one agent per batch) extracts one row per condition;
a second reviewer (another agent) re-checks every value against the source, removes numbers
cited from other studies, adds missed conditions and logs every change
(`dados_S_phi/mudancas_verificacao.csv`). The proportion of values changed by the checker is
reported as the extraction error rate. `busca/juntar_extracao.py` builds `dados_S_phi/S_phi.csv`
(one row per condition, S recomputed from E_o and E_c when possible, consistency flags) and
`dados_S_phi/estudos_extraidos.csv` (one row per study with the risk-of-bias flags).

One row per experimental condition (cover × φ × period/site). Fields:

study_id, doi, year, country, climate (Köppen), scale (pan/tank/wind tunnel/pond/dam/reservoir/
lake), water area (m²), depth (m), cover class (balls, discs, hexagons, plates, rafts, modular,
shade cloth, FPV, perforated sheet, other), element size (m), material, colour, floating vs
suspended, φ, φ source (reported/computed), gap length scale (m), E_o and E_c with units,
S, S/φ, period length, season, mean wind speed and height, mean air temperature, VPD or RH,
radiation, measurement method for E, control type, replication, model-based (yes/no),
location of the numbers in the source (table/figure/page), digitised from figure (yes/no),
full text read (yes/abstract only), extraction confidence (high/medium/low), notes.

Studies by the present authors (Articles 1 and 2) enter as rows flagged "same authors".

## 7. Appraisal

Each row gets a risk-of-bias flag on: control comparability (same forcing, same size), φ
definition, measurement method (resolution vs expected difference), period length, and whether
S includes the evaporation from the gaps.

## 8. Synthesis

S versus φ plots by scale and cover class; S/φ against wind speed and gap scale; a simple
meta-regression (S/φ ~ φ + log gap scale + wind + scale class, with study random effects);
narrative synthesis of mechanisms against the theory of Section 4.
