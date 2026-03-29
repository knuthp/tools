# tools
Mischellaneous HTML+JavaScript or python script tools built mostly with the help of LLMs.

This collection is an experiment in prompt-driven development with very low stakes.

Inspired by Simon Willison <https://github.com/simonw/tools>


## Browser tools

### Geographic information
* [Sporet vehicles M365 Copilot](./vehicles_m365_copilot.html) Show cross country track prepping vehicles. Built with M365 Copilot
* [Sporet vehicles Claude](./vehicles_claude.html) Show cross country track prepping vehicles. Built with Claude Sonnet
* [Sporet vehicles Gemini](./vehicles_gemini.html) Show cross country track prepping vehicles. Built with Google Gemini
* [Oslo Air Traffic](./oslo_planes.html) Live aircraft tracking around Oslo using adsb.lol API.
* [Entur SIRI-Lite Real-Time Map](./entur_siri_lite.html) Real-time public transport vehicles in Norway using Entur API.
* [Entur Stops Map](./entur_stops_deckgl.html) Map of transit stops loaded from Parquet using DuckDB-Wasm and Deck.gl.
* [AIS Trips Animation](./ais_trips.html) Animate a day of AIS vessel traffic using Deck.gl and DuckDB-Wasm.
* [Entur Trips Animation](./entur_trips.html) Animate a day of Entur vehicle monitoring traffic using Deck.gl and DuckDB-Wasm.

### DNT cabins, trips, etc

* [API (graphql) browser](./dnt-graphql-explorer.html) Explore what data is available from DNT graphql API.

### Genealogy
* [Genealogy Tree Viewer](./genealogy_tree.html) A D3.js powered genealogy tree viewer that shows ancestors (parents above children). Supports multiple JSON data files.

### Games
* [Thro' the Wall](./thro_the_wall.html) ZX Spectrum style breakout clone.
* [Fox Platformer](./fox_platformer.html) A Mario-style platformer featuring a Red Fox and Siberian Huskies.


## Python tools

### Geographic information

* [Entur GTFS to GeoParquet](./python/entur_gtfs_to_geoparquet.py) Python script to download Entur GTFS and convert to (Geo)Parquet. Run with `uv run python/entur_gtfs_to_geoparquet.py`.
* [AIS to single day feather](./python/fetch_ais_to_arrow.py) Python script to download hugging face AIS data for one day and save as arrow (feather).  Run with `uv run python/fetch_ais_to_arrow.py`
* [Estimate Vehicle Positions (DuckDB)](./python/estimate_vehicle_positions_duckdb.py) Python script to estimate real-time vehicle positions from SIRI ET data using DuckDB for interpolation. Run with `uv run python/estimate_vehicle_positions_duckdb.py`.
