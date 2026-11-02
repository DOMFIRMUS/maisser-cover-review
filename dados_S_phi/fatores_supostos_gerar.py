import json, re, sys
from pathlib import Path
base = Path(sys.argv[1])
txt = (base / "fatores_supostos_entrada.md").read_text(encoding="utf-8")
ent = []
for bloco in txt.split("\n### ")[0:]:
    bloco = bloco.lstrip("# ").strip()
    if not bloco:
        continue
    cab = bloco.splitlines()[0]
    scr = next((l for l in bloco.splitlines() if l.startswith("screening:")), "")
    partes = [p.strip() for p in cab.split("|")]
    key = partes[1].replace("bibkey", "").strip()
    is_pv = bool(re.search(r"\bpv\b|fpv|fspv|photovolt|solar", cab + " " + scr, re.I))
    ent.append({"id": partes[0], "key": key, "year": partes[2], "title": partes[4] if len(partes) > 4 else "",
                "is_pv": is_pv, "factor": None, "basis": None, "phi": None, "note": scr.replace("screening: ", "")})
# Factors verified in the abstracts (busca/brutos/resumos.json) on 2026-10-31.
U, T = "under_cover_area", "total_water_surface"
num = {
 "Aznaveh2026": (0.80, U, None, "stated '80 % FPV efficiency' applied to the covered area (5-20 % cover); 19,591,093 -> 16,456,518 m3 at 20 % = 0.8 x 0.2"),
 "AbdElhamid2021": (0.70, U, None, "back-calculated: 2.1, 4.2, 6.3, 8.4 x 10^9 m3 saved at 25-100 % cover of 12.0 x 10^9 m3/yr"),
 "Santos2022": (1.0, U, None, "open-water evaporation times covered area"),
 "Hussain2024": (1.0, U, None, "Linacre evaporation times covered area"),
 "Prabawanti2026": (1.0, U, None, "saving from change in exposed area"),
 "Mittal2017": (1.0, U, None, "empirical evaporation times covered area"),
 "Mouhaya2025": (1.0, U, None, "FAO-56 evaporation times covered area"),
 "Azami2017": (1.0, U, None, "energy-budget evaporation times covered area"),
 "Sapthanakorn2021": (1.0, U, None, "Shuttleworth evaporation times FPV area"),
 "Kurt2025": (1.0, U, None, "Penman/Linacre/ANN evaporation times covered area"),
 "Kaab2025": (0.450, T, 0.6, "1,389,597 -> 764,278 m3/yr at 60 % cover of canals"),
 "Trmkc2026": (0.5765, T, 0.8, "513,268 m3/yr reduced by 295,919 m3/yr at 80 % cover"),
 "Costa2021": (0.167, T, None, "16.7 % reservoir evaporation reduction; phi not reported"),
 "Abdelgaied2023": (None, "unclear", None, "61.71 % reported; basis unclear"),
}
for e in ent:
    if e["key"] in num:
        f, b, p, n = num.pop(e["key"])
        e.update(factor=f, basis=b, phi=p, note=n)
assert not num, num
out = {"source": "fatores_supostos_entrada.md (127 assumed-factor records); factors verified against the abstracts in busca/brutos/resumos.json",
       "fields": "is_pv: PV in title or screening note; factor: assumed or implied evaporation reduction; basis: under_cover_area (per unit covered area) or total_water_surface; phi: covered fraction, for whole-surface factors",
       "n_records": len(ent), "n_pv": sum(e["is_pv"] for e in ent), "fatores": ent}
(base / "fatores_supostos.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(out["n_records"], out["n_pv"], sum(e["factor"] is not None for e in ent))
