#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

RSCRIPT_BIN="Rscript"

if ! command -v "$RSCRIPT_BIN" >/dev/null 2>&1; then
  r_roots=(
    "/c/Program Files/R"
    "/mnt/c/Program Files/R"
  )

  for r_root in "${r_roots[@]}"; do
    if [ -d "$r_root" ]; then
      WINDOWS_RSCRIPT="$(find "$r_root" -path "*/bin/Rscript.exe" -print 2>/dev/null | sort -V | tail -n 1)"
      if [ -n "$WINDOWS_RSCRIPT" ]; then
        RSCRIPT_BIN="$WINDOWS_RSCRIPT"
      fi
    fi
  done
fi

if ! command -v "$RSCRIPT_BIN" >/dev/null 2>&1 && [ ! -x "$RSCRIPT_BIN" ]; then
  if command -v powershell.exe >/dev/null 2>&1; then
    WINDOWS_RSCRIPT="$(powershell.exe -NoProfile -Command '$r = Get-ChildItem "C:\Program Files\R" -Recurse -Filter Rscript.exe -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1 -ExpandProperty FullName; if ($r) { $r -replace "\\", "/" }' | tr -d '\r')"
    if [ -n "$WINDOWS_RSCRIPT" ]; then
      RSCRIPT_BIN="${WINDOWS_RSCRIPT/C:/\/mnt\/c}"
    fi
  fi
fi

if ! command -v "$RSCRIPT_BIN" >/dev/null 2>&1 && [ ! -x "$RSCRIPT_BIN" ]; then
  echo "Error: Rscript is not installed or is not on PATH." >&2
  echo "Install R first, then re-run this script." >&2
  exit 1
fi

echo "Installing required R packages..."
"$RSCRIPT_BIN" --vanilla - <<'RSCRIPT'
cran_packages <- c(
  "bookdown",
  "rmarkdown",
  "knitr",
  "plotly",
  "reshape2",
  "png",
  "BiocManager"
)

missing_cran <- cran_packages[!vapply(cran_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_cran)) {
  install.packages(missing_cran, repos = "https://cloud.r-project.org")
}

if (!requireNamespace("EBImage", quietly = TRUE)) {
  BiocManager::install("EBImage", ask = FALSE, update = FALSE)
}
RSCRIPT

echo "Rendering bookdown project to _book..."
rm -rf _book
"$RSCRIPT_BIN" --vanilla -e "bookdown::render_book('index.Rmd', output_dir = '_book')"

if [ ! -d "_book" ]; then
  echo "Error: bookdown render did not create _book." >&2
  exit 1
fi

echo "Refreshing docs from _book..."
rm -rf docs
cp -R _book docs

echo "Staging generated site in docs..."
git add -A -- docs
if ! git diff --cached --quiet -- docs; then
  git commit -m "Build and publish book"
else
  echo "docs is already up to date; no commit needed."
fi

echo "Build complete: _book rendered, copied to docs, and committed."
