from fastapi import FastAPI, HTTPException
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

# Static files configuration
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
static_dir = os.path.abspath(static_dir)

# Routes explicites AVANT le mount static (priorité)
@app.get("/static/app.js")
async def serve_app_js():
    app_js_path = os.path.join(static_dir, "app.js")
    print(f"🎯 Serving app.js from: {app_js_path}")
    print(f"🎯 File exists: {os.path.exists(app_js_path)}")
    if os.path.exists(app_js_path):
        return FileResponse(app_js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")

@app.get("/")
async def serve_index():
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {"message": "Interface web non disponible. Utilisez /docs pour l'API."}

@app.get("/debug/paths")
async def debug_paths():
    """Debug endpoint pour vérifier les chemins en production"""
    return {
        "root_path": ROOT_PATH,
        "static_dir": static_dir,
        "static_exists": os.path.exists(static_dir),
        "app_js_exists": os.path.exists(os.path.join(static_dir, "app.js")),
        "index_html_exists": os.path.exists(os.path.join(static_dir, "index.html")),
        "expected_static_url": f"{ROOT_PATH}/static/app.js" if ROOT_PATH else "/static/app.js",
        "files_in_static": os.listdir(static_dir) if os.path.exists(static_dir) else []
    }

# Mount static files APRÈS les routes explicites
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"📁 Static files mounted from: {static_dir}")
    print(f"🌐 Static files available at: /static/ and {ROOT_PATH}/static/")

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)