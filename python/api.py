from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title="toolsapi.knuthp.no")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tools.knuthp.no",
        "https://knuthp.github.io",
    ],
    allow_origin_regex=r"https://.*\.knuthp\.workers\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)


GEOJSON_PATH = Path("data/entur_et/positions_interpolated.geojson")

@app.get("/data/entur_et/positions_interpolated.geojson")
async def get_positions():
    return FileResponse(
        GEOJSON_PATH,
        media_type="application/geo+json",
        filename="positions_interpolated.geojson",
    )

@app.get("/health")
async def health():
    return {"ok": True}
