#!/bin/bash
# scripts/cf_publish.sh

set -e

# 1. Clean build
echo "Cleaning _build directory..."
rm -rf _build
mkdir -p _build

# 2. Copy files with 25MB limit
echo "Copying HTML files and data directory (max size 25MB)..."

# Copy HTML files from root (excluding those already in _build or other dirs)
find . -maxdepth 1 -name "*.html" -not -path "./_build/*" | while read -r f; do
    size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
    if [ "$size" -le 26214400 ]; then  # 25MB in bytes
        cp "$f" _build/
    fi
done

# Copy data directory (preserving structure)
if [ -d "data" ]; then
    mkdir -p _build/data
    find data -type f | while read -r f; do
        size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
        if [ "$size" -le 26214400 ]; then
            dest="_build/${f}"
            mkdir -p "$(dirname "$dest")"
            cp "$f" "$dest"
        fi
    done
fi

# 3. Generate index.html from README.md (Better Markdown)
echo "Generating index.html from README.md..."

# Create the final index.html with GitHub-like CSS
cat <<EOF > _build/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Tools Collection</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css">
    <style>
        .markdown-body {
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
        }
        @media (max-width: 767px) {
            .markdown-body {
                padding: 15px;
            }
        }
    </style>
</head>
<body class="markdown-body">
EOF

# Use uv to run markdown_py with extensions and append to index.html
# 'extra' enables tables, fenced code blocks, etc.
# 'toc' enables [TOC] marker.
# 'sane_lists' for better list behavior.
uv tool run --from markdown markdown_py -x extra -x toc -x sane_lists README.md >> _build/index.html

cat <<EOF >> _build/index.html
</body>
</html>
EOF

echo "Build complete! Output is in the _build/ directory."
