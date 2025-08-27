from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.router import api_router
from app.core.config import settings
import os

# Configuration pour déploiement avec base path
ROOT_PATH = os.getenv("ROOT_PATH", "")

app = FastAPI(
    title="Cartographie Sémantique",
    description="API pour cartographier sémantiquement un site web",
    version="1.0.0",
    root_path=ROOT_PATH
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
static_dir = os.path.abspath(static_dir)  # Chemin absolu
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"📁 Static files mounted from: {static_dir}")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def serve_index():
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {"message": "Interface web non disponible. Utilisez /docs pour l'API."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)