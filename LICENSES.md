Sources and Licenses
====================

This project uses the following openly licensed datasets to build the interlinear layer.

- Scrivener’s Textus Receptus 1894 (Robinson edition, parsed with Strong’s and morph)
  - Source: https://github.com/byztxt/greektext-textus-receptus (parsed/JOH.UTR)
  - License: Public Domain (copy freely)

- STEP Bible Lexicon (TBESG – Translators Brief lexicon of Extended Strongs for Greek)
  - Source: https://github.com/STEPBible/STEPBible-Data (Lexicons/TBESG ... CC BY)
  - License: CC BY 4.0 (attribution required)

- Open Scriptures Hebrew Bible (WLC text + OSHB morphology)
  - Source: https://github.com/openscriptures/morphhb (WLC OSIS + morphology)
  - License: CC BY 4.0 (OSHB); WLC is Public Domain
  - Required attribution: “Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb”

- Albanian verses (existing site text)
  - Source: Already present under `site/data/verses.json`
  - License: Carried as-is from the current site (not re-licensed); usage limited to rendering on this site. Replaceable.

Build Notes
-----------
Exact source versions are pinned in `sources.yaml` and checksums recorded in `sources.lock` by `scripts/fetch_sources.py`.

Attribution
-----------
The UI footer acknowledges TR 1894 (Public Domain) and STEPBible TBESG (CC BY 4.0). Please retain this notice in derived works.
