# Build the CS222 Beamer deck (main_uit.tex is the single master file).
#   make          -> crop figures from the papers, then compile twice
#   make figures  -> regenerate slides/figure/ from slides/source/
#   make zip      -> overleaf_uit.zip: the UIT-styled deck for Overleaf
#   make zip-uit  -> alias of `make zip`
#   make clean    -> remove build artefacts

# BasicTeX lives outside the default PATH; find it without touching the shell.
export PATH := /Library/TeX/texbin:$(PATH)
XELATEX ?= /Library/TeX/texbin/xelatex
PYTHON  ?= ../.venv-slides/bin/python
FLAGS   := -interaction=nonstopmode -halt-on-error
MASTER  := main_uit.tex

.PHONY: all figures zip zip-uit clean

all: figures
	printf '$$pdf_mode = 5;\n' > latexmkrc
	$(XELATEX) $(FLAGS) $(MASTER)
	$(XELATEX) $(FLAGS) $(MASTER)
	@rm -f latexmkrc
	@echo "--- overfull/failed boxes:"
	@grep -E "Overfull \\\\[vh]box|^!" main_uit.log || echo "none"

figures:
	$(PYTHON) tools/crop_figures.py

zip:
	@rm -f overleaf_uit.zip
	@printf '$$pdf_mode = 5;\n' > latexmkrc
	@zip -qr overleaf_uit.zip $(MASTER) latexmkrc parts fonts figure/deck figure/bg figure/t2l figure/gepa \
	  -x '*.DS_Store'
	@rm -f latexmkrc
	@unzip -l overleaf_uit.zip | tail -1

zip-uit: zip

clean:
	rm -f main_uit.aux main_uit.log main_uit.nav main_uit.out main_uit.snm main_uit.toc main_uit.vrb \
	      main_uit.pdf latexmkrc overleaf.zip overleaf_uit.zip
