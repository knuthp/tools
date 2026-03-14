# Agent Instructions for tools-collection

This repository contains a collection of miscellaneous HTML, JavaScript, and Python tools, often built with the assistance of LLMs.

## Project Structure
- `*.html`: Single-file tools (Deck.gl, Leaflet, etc.)
- `*.py`: Python scripts and utilities.
- `README.md`: Human-readable list of tools and descriptions.
- `.github/workflows/static.yml`: Deployment workflow that generates `index.html` from `README.md`.

## Guidelines for Adding New Tools
- **Standalone Files**: Prefer single HTML files with no backend for frontend tools.
- **Update README**: Always add a link and a short description of the new tool to `README.md`.
- **Deck.gl Best Practices**:
  - Use `getAngle: d => -(d.track || 0)` for North-pointing icons to align clockwise headings with the map.
  - Base64 encode SVG data for the `IconLayer`.
  - Set `mask: true` to enable color tinting via the `getColor` accessor.

## Programmatic Checks
Before submitting any changes, you MUST run the following checks:

### 1. JavaScript & HTML Linting
Ensure all JavaScript (including code within HTML files) follows basic standards.
```bash
npm install
npm run lint
```

### 2. Python Linting
Use Ruff for all Python files.
```bash
ruff check .
```

### 3. Verification Scripts
If you modify `oslo_planes.html` or similar tools, run the corresponding verification script:
```bash
python verify_oslo_planes.py
```
*Note: This requires Playwright for Python.*

## Deployment Considerations
The project is deployed via GitHub Pages.
- `index.html` is generated from `README.md` using Pandoc.
- Do not edit `index.html` directly if it exists in a build context; it is a generated artifact.
- Ensure your changes do not break the `static.yml` workflow (e.g., by using Markdown features that Pandoc might struggle with).
