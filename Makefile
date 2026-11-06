# PaperDIY PDA Terminal: rebuild everything from source.
#
#   make setup       pinned Python packages for the CAD scripts and the host tests
#   make cad         fetch the pinned original STLs, build every STL and run the fit / motion checks
#   make 3mf         print plates for the Bambu Lab A1 mini (cad/3mf/)
#   make verify      rebuild and compare with cad/out/MANIFEST.json (what is committed)
#   make report      slicer estimates and stability warnings (needs prusa-slicer) -> cad/out/print_report.md
#   make render      README / assembly images (needs Node.js; downloads Chromium for Playwright)
#   make test        host tests of the firmware's terminal emulator (g++, Python with pyte)
#   make firmware    ESP-IDF v5.5.6 build (run `. $IDF_PATH/export.sh` first); checks it against prebuilt/
#   make firmware-docker   the same inside espressif/idf:v5.5.6
#   make manifest    after a deliberate design change: record the new CAD outputs
PYTHON      ?= python3
ORIGINAL    ?= $(HOME)/phone-enclosure
IDF_VERSION := v5.5.6
export PHONE_ENCLOSURE_STL ?= $(ORIGINAL)/STL

.PHONY: all setup original cad 3mf verify report manifest render test firmware firmware-check firmware-docker

all: 3mf

setup:
	$(PYTHON) -m pip install -r cad/requirements.txt -r firmware/test/host/requirements.txt

original:
	cad/tools/fetch_original.sh $(ORIGINAL)

cad: original
	cd cad && $(PYTHON) src/build.py

3mf: cad
	cd cad && $(PYTHON) src/export_3mf.py

verify: 3mf
	cd cad && $(PYTHON) tools/manifest.py --check

report: 3mf
	cd cad && $(PYTHON) tools/print_report.py

manifest: 3mf
	cd cad && $(PYTHON) tools/manifest.py --write

render:
	cd docs/render && npm ci && npx playwright install chromium && npm run render
	$(PYTHON) docs/hinge_figure.py docs/images/hinge_screws.png
	$(PYTHON) docs/coupons_figure.py docs/images/plate0_coupons.png
	$(PYTHON) docs/paperdiy_figure.py docs/images/paperdiy_mount.png

test:
	$(MAKE) -C firmware/test/host test PYTHON=$(PYTHON)

firmware:
	@test -n "$$IDF_PATH" || { echo "run '. <esp-idf $(IDF_VERSION)>/export.sh' first"; exit 1; }
	cd firmware && ./fetch_deps.sh && idf.py build && idf.py merge-bin -o paperdiy-term-merged.bin
	$(MAKE) firmware-check

firmware-check:
	@cd firmware && sha256sum build/paperdiy-term-merged.bin && \
	if cmp -s build/paperdiy-term-merged.bin prebuilt/paperdiy-term-merged.bin; then \
	  echo "identical to prebuilt/paperdiy-term-merged.bin (reproducible build)"; \
	else echo "differs from prebuilt/ (other ESP-IDF version, or changed sources)"; exit 1; fi

firmware-docker:
	docker run --rm -v "$(CURDIR)/firmware:/project" -w /project espressif/idf:$(IDF_VERSION) bash -c \
	  "git config --global --add safe.directory '*' && ./fetch_deps.sh && idf.py build && idf.py merge-bin -o paperdiy-term-merged.bin"
	$(MAKE) firmware-check
