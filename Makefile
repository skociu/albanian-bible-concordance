PY=python

.PHONY: setup fetch build\:data build\:data-ot build\:data-ot-all build\:mt build\:exod validate validate-ot validate-mt validate-exod serve all

setup:
	$(PY) -m pip install --upgrade pip
	@if exist requirements.txt ($(PY) -m pip install -r requirements.txt) else (echo no requirements)

fetch:
	$(PY) scripts/fetch_sources.py

build\:data:
	$(PY) scripts/tr_to_json.py
	$(PY) scripts/build_interlinear.py --input .cache/build/tr/john/1.json --output site/data/john/1.json

build\:data-ot:
	$(PY) scripts/oshb_to_json.py --book Gen --chapter 1
	$(PY) scripts/build_interlinear.py --input .cache/build/ot/genesis/1.json --output site/data/genesis/1.json

build\:data-ot-all:
	@echo Building OSHB OT for all chapters...
	$(PY) scripts/build_interlinear_ot_all.py

build\:mt:
	$(PY) scripts/tr_to_json.py --book MT --chapter 1
	$(PY) scripts/build_interlinear.py --input .cache/build/tr/matthew/1.json --output site/data/matthew/1.json

build\:exod:
	$(PY) scripts/oshb_to_json.py --book Exod --chapter 1
	$(PY) scripts/build_interlinear.py --input .cache/build/ot/exodus/1.json --output site/data/exodus/1.json

validate:
	$(PY) scripts/validate_schema.py site/data/john/1.json

validate-ot:
	$(PY) scripts/validate_schema.py site/data/genesis/1.json

validate-mt:
	$(PY) scripts/validate_schema.py site/data/matthew/1.json

validate-exod:
	$(PY) scripts/validate_schema.py site/data/exodus/1.json

serve:
	$(PY) -m http.server -d site 8080

all: fetch build\:data build\:data-ot validate validate-ot serve
