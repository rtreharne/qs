
# RBook

Title TBD.

Run `./build.sh` (macOS/Linux/WSL) or `./build.ps1` (Windows PowerShell) to compile the book. The scripts install the required R packages, render the site into `_book`, copy it to `docs`, and commit any generated site changes so GitHub Pages can publish them. Run the build from a clean Git working tree and configure your Git author name and email first.

Open the "index.html" file to see what it looks like

If you want to create a pdf file:

bookdown::render_book("index.Rmd", output_format = "bookdown::pdf_book")
