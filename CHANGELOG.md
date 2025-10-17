## 2025-10-13

- MVP: Interlinear layer for Gjoni (John) 1
  - Added build pipeline and schema (`schemas/interlinear_verse.schema.json`)
  - Fetch pinned sources (`scripts/fetch_sources.py`, `sources.yaml`, `sources.lock`)
  - MorphGNT to verse JSON (`scripts/morphgnt_to_json.py`)
  - Merge Albanian + attach gloss/Strong’s (`scripts/build_interlinear.py`)
  - Schema validation (`scripts/validate_schema.py`)
  - Frontend: `site/assets/js/interlinear.js`, `site/assets/js/app.js`, `site/assets/css/interlinear.css`
  - UI toggle “Ndiz Interlinear” for Gjoni 1; token tooltips; Strong’s links back to the concordance
  - CI: updated `gh-pages.yml` to build and validate interlinear data
  - Docs: README updates and `LICENSES.md`

Reproduce:

- `make all` or run: `python scripts/fetch_sources.py && python scripts/morphgnt_to_json.py && python scripts/build_interlinear.py && python scripts/validate_schema.py && python -m http.server -d site 8080`

