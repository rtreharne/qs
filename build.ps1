$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$Rscript = Get-Command Rscript -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty Source

if (-not $Rscript) {
    $Rscript = Get-ChildItem "C:\Program Files\R" -Recurse -Filter Rscript.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        Select-Object -Last 1 -ExpandProperty FullName
}

if (-not $Rscript) {
    Write-Error "Rscript is not installed or is not on PATH. Install R first, then re-run this script."
}

Write-Host "Using Rscript: $Rscript"
Write-Host "Installing required R packages..."

$InstallScript = @'
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

'@

$InstallScript | & $Rscript --vanilla -
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Rendering bookdown project to _book..."
if (Test-Path "_book") {
    Remove-Item "_book" -Recurse -Force
}

& $Rscript --vanilla -e "bookdown::render_book('index.Rmd', output_dir = '_book')"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path "_book")) {
    Write-Error "bookdown render did not create _book."
}

Write-Host "Refreshing docs from _book..."
if (Test-Path "docs") {
    Remove-Item "docs" -Recurse -Force
}

Copy-Item "_book" "docs" -Recurse

Write-Host "Staging generated site in docs..."
git add -A -- docs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

git diff --cached --quiet -- docs
$DiffExitCode = $LASTEXITCODE
if ($DiffExitCode -eq 1) {
    git commit -m "Build and publish book"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} elseif ($DiffExitCode -eq 0) {
    Write-Host "docs is already up to date; no commit needed."
} else {
    Write-Error "Could not inspect staged docs changes."
}

Write-Host "Build complete: _book rendered, copied to docs, and committed."
