"""Melodiva AI — independent music generation API and song library."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from full_song import router as full_song_router
from song_extension import router as extensions_router
from text_to_song import router as text_song_router
from lyrics_generator import router as lyrics_router
from generated_storage import router as library_router
from commercial_licensing import router as licensing_router

app = FastAPI(title="Melodiva AI", version="1.0.0")
app.include_router(full_song_router)
app.include_router(extensions_router)
app.include_router(text_song_router)
app.include_router(lyrics_router)
app.include_router(library_router)
app.include_router(licensing_router)

@app.get("/health")
def health():
    return {"ok": True, "service": "melodiva-ai"}

frontend_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
