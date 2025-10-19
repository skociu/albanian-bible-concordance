Albanian Bible (Alb) SQL dump is included as `Alb.sql.txt` (sourced from the Scrollmapper Bible databases).

Quick start (build a local concordance):

- Requires Python 3.9+
- Build the SQLite database: `python scripts/build_concordance.py build`
- Search a word: `python scripts/build_concordance.py search dashuri`
- List most frequent lemmas: `python scripts/build_concordance.py top --limit 50`
- Index Strong's (Hebrew/Greek) from interlinear JSON and search by code:
   - `python scripts/build_concordance.py build-strongs --site site`
   - Example: `python scripts/build_concordance.py search G3056` or `python scripts/build_concordance.py search H07225`

Notes:

- The source text contains encoding artifacts (e.g., `eI^` for `ë`, `cI\x15` for `ç`). The importer normalizes these and performs accent-insensitive token search.
- Output DB: `alb_concordance.sqlite` with tables: `books`, `verses`, `tokens`.

Roadmap toward a Strong’s-like concordance:

- Add original-language layers (Hebrew/Greek with Strong’s numbers) into separate tables.
- Create alignment mapping between Albanian tokens/phrases and Strong’s lemmas per verse.
- Expose lookups: Albanian word → Strong’s entries → definitions/morphology → all occurrences.
- Optional: FTS5 index for fast phrase search and a small web UI.

Minimal Web UI

- Run: `python scripts/web_ui.py --db alb_concordance.sqlite --port 8000`
- Open: `http://127.0.0.1:8000`
- Features: search (accent-insensitive), Strong's search (`G####`/`H####`), browse books/chapters, export results (HTML/TXT/CSV). HTML export is print-friendly.
 - Static site: run `python scripts/build_concordance.py build-strongs --site site` then `python scripts/build_site_index.py --out site` to generate `site/data/strongs/strongs_H.json` and `strongs_G.json` for instant Strong's lookups in the UI.

Export Results (for printing)

- CLI export: `python scripts/build_concordance.py export dashuri --format html --limit 200`
- Outputs to `exports/` by default. Formats: `html`, `txt`, `csv`.

Source reference:

- https://raw.githubusercontent.com/scrollmapper/bible_databases/refs/heads/master/formats/sql/Alb.sql

Publish Free on GitHub Pages

- What it is: a static site in `site/` that serves client-side search using JSON indexes. No server needed.
- One-time setup: in your repo, enable Pages at Settings → Pages, Source: GitHub Actions.
- Deploy: push to `main` (or `master`). The workflow `.github/workflows/gh-pages.yml` builds the DB and JSON and publishes `site/`.
- Local preview: build DB, run `build-strongs`, then `python scripts/build_site_index.py --out site` and serve it locally (fetch needs HTTP): `python -m http.server -d site 8080` then open `http://127.0.0.1:8080`.
- Data size: indexes are sharded by first letter; verses are a single JSON file. We can further shard verses per book if needed.

Manual deploy with git subtree (site/ -> gh-pages)
-------------------------------------------------

If you prefer pushing the static site directly from the `site/` folder to the `gh-pages` branch (without a CI build), use `git subtree`:

1) One‑time: make sure the remote and the `gh-pages` branch exist

   - `git remote -v` (should show `origin`)
   - If `gh-pages` doesn’t exist yet, GitHub will create it on first push below.

2) Deploy the current `site/` contents to `gh-pages`

   - `git subtree push --prefix site origin gh-pages`

   This “splits” the repo history to only the `site/` subdirectory and fast‑forwards `origin/gh-pages` to that snapshot. Treat `gh-pages` as generated output — don’t edit it directly.

Alternative (when fast‑forward fails)

   - `git subtree split --prefix site -b ghpages-tmp`
   - `git push origin ghpages-tmp:gh-pages`
   - `git branch -D ghpages-tmp`

3) Configure Pages (once)

   - Repo Settings → Pages → Source: `Deploy from a branch`

   - Branch: `gh-pages` (root)

4) Local preview before deploy

   - `python -m http.server --directory site 8080` → open `http://127.0.0.1:8080`

Notes

- `gh-pages` is overwritten by deploys; keep sources on `main` and avoid manual edits on `gh-pages`.
- If you later switch to GitHub Actions, keep `site/` as the artifact output and let CI push to `gh-pages` automatically.

Interlinear MVP (Gjoni 1)
-------------------------

This repo now includes a minimal interlinear layer for John 1 using Scrivener’s Textus Receptus 1894 (Robinson edition, Public Domain) with Strong’s and morphology, plus the Albanian verse line. It is static and rendered from JSON.

One-command build:

- `make all` → fetch sources, build interlinear JSON (TR 1894), validate, and serve locally

Manual steps:

1) `make setup` – install Python deps (optional `jsonschema`)
2) `make fetch` – download pinned sources into `.cache/sources/` and write `sources.lock`
3) `make build:data` – generate `.cache/build/tr/john/1.json` (TR 1894 parsed) and `site/data/john/1.json` (merged with Albanian)
4) `make validate` – JSON Schema validation of `site/data/john/1.json`
5) `make serve` – serve the `site/` folder at http://127.0.0.1:8080

Frontend usage:

- Open Browse → Gjoni → 1. A toggle "Ndiz Interlinear" appears and auto-enables.
- It renders three rows: Greek tokens (clickable Strong's), compact lemma/morph/Strong's, and the Albanian verse text.

Data & Licensing:

- Sources and terms are summarized in `LICENSES.md`. Dataset versions are pinned in `sources.yaml` and checksums are recorded in `sources.lock` for reproducibility.

Old Testament Interlinear (All Chapters)
---------------------------------------

This repo can also build an interlinear layer for the Old Testament (Hebrew, WLC via OSHB) across all chapters.

Steps:

- Fetch sources (includes OSHB XML for all OT books and STEP TBESH gloss): `make fetch`
- Build all OT interlinear chapter JSON files: `make build:data-ot-all`
- Local preview: `make serve` then open `http://127.0.0.1:8080` and browse any OT book; use the “Shiko Interlinear” toggle.

Notes:

- The builder generates `site/data/<book-slug>/<chapter>.json` with `_meta.lang_src = 'heb'` for proper RTL rendering.
- Albanian verse lines are taken from `site/data/verses.json` by matching the Albanian book name in `site/data/books.json`.
- If TBESH gloss is available, token Strong’s like `H0001` are mapped to short glosses per verse under `gloss`.
