# tools
Mischellaneous HTML+JavaScript or python script tools built mostly with the help of LLMs.

This collection is an experiment in prompt-driven development with very low stakes.

Inspired by Simon Willison <https://github.com/simonw/tools>


## Geographic information
* [Sporet vehicles M365 Copilot](./vehicles_m365_copilot.html) Show cross country track prepping vehicles. Built with M365 Copilot
* [Sporet vehicles Claude](./vehicles_claude.html) Show cross country track prepping vehicles. Built with Claude Sonnet
* [Sporet vehicles Gemini](./vehicles_gemini.html) Show cross country track prepping vehicles. Built with Google Gemini
* [Oslo Air Traffic](./oslo_planes.html) Live aircraft tracking around Oslo using adsb.lol API.
* [Entur SIRI-Lite Real-Time Map](./entur_siri_lite.html) Real-time public transport vehicles in Norway using Entur API.
* [Entur Stops Map](./entur_stops_deckgl.html) Map of transit stops loaded from Parquet using DuckDB-Wasm and Deck.gl.
* [Entur GTFS to GeoParquet](./python/entur_gtfs_to_geoparquet.py) Python script to download Entur GTFS and convert to (Geo)Parquet. Run with `uv run python/entur_gtfs_to_geoparquet.py`.

## Genealogy
* [Genealogy Tree Viewer](./genealogy_tree.html) A D3.js powered genealogy tree viewer that shows ancestors (parents above children). Supports multiple JSON data files.

## Games
* [Thro' the Wall](./thro_the_wall.html) ZX Spectrum style breakout clone.
* [Fox Platformer](./fox_platformer.html) A Mario-style platformer featuring a Red Fox and Siberian Huskies.
