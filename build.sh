#!/bin/bash

# Knit all .Rmd files (index.Rmd last)
echo "Knitting 01.Rmd..."
Rscript -e "bookdown::render_book('01.Rmd')" && echo "01.Rmd knitted successfully." || echo "Error knitting 01.Rmd."

echo "Knitting 02.Rmd..."
Rscript -e "bookdown::render_book('02.Rmd')" && echo "02.Rmd knitted successfully." || echo "Error knitting 02.Rmd."

echo "Knitting 03.Rmd..."
Rscript -e "bookdown::render_book('03.Rmd')" && echo "03.Rmd knitted successfully." || echo "Error knitting 03.Rmd."

echo "Knitting index.Rmd (last)..."
Rscript -e "bookdown::render_book('index.Rmd')" && echo "index.Rmd knitted successfully." || echo "Error knitting index.Rmd."

# Rename the output directory
if [ -d "_book" ]; then
    if [ -d "docs" ]; then
        echo "Removing existing docs directory..."
        rm -rf docs && echo "docs directory removed." || echo "Error removing docs directory."
    fi
    echo "Renaming _book directory to docs..."
    mv _book docs && echo "Directory renamed successfully." || echo "Error renaming directory."
else
    echo "_book directory does not exist. Exiting."
    exit 1
fi

# Git add, commit, and push
echo "Staging changes for git..."
git add . && echo "Changes staged successfully." || echo "Error staging changes."

echo "Committing changes..."
git commit -m "Update bookdown files" && echo "Changes committed." || echo "Error committing changes."

echo "Pushing changes to remote repository..."
git push && echo "Changes pushed to remote successfully." || echo "Error pushing changes."
