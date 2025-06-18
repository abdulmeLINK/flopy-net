# FLOPY-NET LaTeX Report Compilation

## Makefile for compiling the LaTeX report

# Main target
MAIN = FLOPY-NET_Report
TEX = $(MAIN).tex
PDF = $(MAIN).pdf
BIB = references.bib

# Compiler and flags
LATEX = pdflatex
BIBTEX = bibtex
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error

# Default target
all: $(PDF)

# Build the PDF
$(PDF): $(TEX) $(BIB)
	@echo "Compiling LaTeX document..."
	$(LATEX) $(LATEX_FLAGS) $(TEX)
	$(BIBTEX) $(MAIN)
	$(LATEX) $(LATEX_FLAGS) $(TEX)
	$(LATEX) $(LATEX_FLAGS) $(TEX)
	@echo "Compilation complete: $(PDF)"

# Clean intermediate files
clean:
	@echo "Cleaning intermediate files..."
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot *.fdb_latexmk *.fls *.synctex.gz
	@echo "Clean complete."

# Clean everything including PDF
distclean: clean
	@echo "Removing PDF..."
	rm -f $(PDF)
	@echo "All files cleaned."

# Force rebuild
rebuild: distclean all

# View the PDF (platform-specific)
view: $(PDF)
ifeq ($(OS),Windows_NT)
	start $(PDF)
else
	xdg-open $(PDF)
endif

# Help target
help:
	@echo "Available targets:"
	@echo "  all       - Build the PDF (default)"
	@echo "  clean     - Remove intermediate files"
	@echo "  distclean - Remove all generated files"
	@echo "  rebuild   - Clean and rebuild everything"
	@echo "  view      - Open the PDF in default viewer"
	@echo "  help      - Show this help message"

.PHONY: all clean distclean rebuild view help

# PowerShell alternatives for Windows
.PHONY: build-windows clean-windows view-windows

build-windows:
	@echo "Building PDF using PowerShell..."
	powershell -Command "pdflatex -interaction=nonstopmode $(TEX); bibtex $(MAIN); pdflatex -interaction=nonstopmode $(TEX); pdflatex -interaction=nonstopmode $(TEX)"

clean-windows:
	@echo "Cleaning files using PowerShell..."
	powershell -Command "Remove-Item -Path '*.aux', '*.bbl', '*.blg', '*.log', '*.out', '*.toc', '*.lof', '*.lot', '*.fdb_latexmk', '*.fls', '*.synctex.gz' -ErrorAction SilentlyContinue"

view-windows: $(PDF)
	@echo "Opening PDF..."
	powershell -Command "Start-Process $(PDF)"
