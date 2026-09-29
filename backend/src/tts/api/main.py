"""FastAPI application."""

from fastapi import FastAPI

app = FastAPI(title="IIT-TTS")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
