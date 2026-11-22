# Build the CS222 Beamer deck.
#   make          -> crop figures from the papers, then compile twice
#   make figures  -> regenerate slides/figure/ from slides/source/
#   make zip      -> overleaf.zip with only what Overleaf needs
#   make clean    -> remove build artefacts

XELATEX ?= xelatex
PYTHON  ?= ../.venv-slides/bin/python
FLAGS   := -interaction=nonstopmode -halt-on-error

.PHONY: all figures zip clean

all: figures
	$(XELATEX) $(FLAGS) main.tex
	$(XELATEX) $(FLAGS) main.tex
	@echo "--- overfull/failed boxes:"
	@grep -E "Overfull \\\\[vh]box|^!" main.log || echo "none"

figures:
	$(PYTHON) tools/crop_figures.py

zip:
	@rm -f overleaf.zip
	@zip -qr overleaf.zip main.tex parts figure -x '*.DS_Store' -x 'figure/crops.json'
	@unzip -l overleaf.zip | tail -3

clean:
	rm -f main.aux main.log main.nav main.out main.snm main.toc main.vrb main.pdf overleaf.zip
