# Validation set — measure real drawing→BOQ accuracy

This harness references real villa projects **in place** (it never copies the large
PDFs), so the repo stays lean and runtime performance is unaffected.

## What qualifies as a validation project
A project folder must contain all three:
- architectural drawing — PDF whose name contains `arch`
- structural drawing — PDF whose name contains `str`/`struct`
- ground-truth BOQ — an Excel file that is **not** a system output
  (`*_QTO_HYBRID_TEST.xlsx` etc. are ignored)

Incomplete folders are skipped automatically and listed under `incomplete_projects`.

## Run (cheap — no AI, no copying)
```powershell
# default root = B:\work\trainning  (the 8 clean arch+str+BOQ pairs)
python validation_set/run_validation.py

# point at another folder
python validation_set/run_validation.py --root "B:\work\projects estimation\projects\..."
```
Output: `validation_set/manifest.json` — paths + each project's ground-truth BOQ
parsed into normalized engine keys (excavation, foundation_concrete, …) via the
existing `_extract_real_boqs.extract_from_workbook`.

`manifest.json` is git-ignored (machine-specific absolute paths; regenerate anytime).

## Current verified set (root = trainning)
All **11** projects (1–11) qualify — each has an architectural PDF + structural PDF
+ ground-truth BOQ (parsed to 23–29 items). The detector handles real-world naming
variants (`AR-…` for architectural, `STC`/`stc` for structural).
Note: 5 and 7 share the same BOQ file — treat as one if deduping.

## Next step — the accuracy sweep (heavy, opt-in)
`--run-engine` is the place to wire the full pass: load each project's two PDFs →
run the extraction + `build_boq_dataframe_from_project` → diff computed vs ground-truth
per item → emit a per-item accuracy report (% deviation, 🟢/🟡/🔴).
It is **not** run automatically because it calls the AI extractor (Gemini cost + time).

## Adding more projects
Point `--root` at any folder of clean `arch + str + BOQ` projects. Noisy folders with
40–100 PDFs (NOCs, soil reports, approvals) need the right two sheets isolated first —
the auto-detector picks one `arch` + one `str` PDF per folder.
