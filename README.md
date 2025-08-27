# Cartographie Sémantique

Application FastAPI pour cartographier sémantiquement un site web en identifiant les pages proches sémantiquement mais lointaines en termes de liens.

## Fonctionnalités

- Upload et validation de CSV avec colonnes `url,contenu`
- Génération d'embeddings via micro-service externe
- Clustering sémantique (UMAP + HDBSCAN ou K-means)
- Calcul de proximité sémantique vs distance de liens
- Projection 2D pour visualisation
- API REST complète avec exports

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` vers `.env` et ajustez les paramètres :

```bash
cp .env.example .env
```

## Démarrage

```bash
python -m app.main
```

Ou avec uvicorn :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Projets
- `POST /api/v1/projects` - Créer un projet
- `GET /api/v1/projects` - Lister les projets
- `GET /api/v1/projects/{id}` - Détails d'un projet

### Pipeline
- `POST /api/v1/projects/{id}/import` - Upload CSV
- `POST /api/v1/projects/{id}/embed` - Générer embeddings
- `POST /api/v1/projects/{id}/analyze` - Analyser (clustering + scoring)

### Résultats
- `GET /api/v1/projects/{id}/clusters` - Clusters trouvés
- `GET /api/v1/projects/{id}/proximities` - Anomalies de proximité
- `GET /api/v1/projects/{id}/preview` - Aperçu avec projection 2D
- `GET /api/v1/projects/{id}/export/{format}` - Export (csv, json, parquet)

## Format CSV d'entrée

Le CSV doit contenir les colonnes :
- `url` : URL canonique de la page
- `contenu` : texte nettoyé (si vide, l'URL sera utilisée pour l'embedding)

## Micro-service d'embeddings

L'application s'attend à un service externe sur `/embed` qui :
- Accepte `{"items": [{"type": "text|url", "value": "..."}]}`
- Retourne `{"vectors": [[...]], "dims": 1024, "normalized": true}`

## Architecture

```
app/
├── main.py              # Point d'entrée FastAPI
├── core/
│   └── config.py        # Configuration
├── models/
│   └── schemas.py       # Modèles Pydantic
├── api/v1/
│   └── endpoints/
│       └── projects.py  # Endpoints projets
└── services/
    ├── ingest.py        # Ingestion CSV
    ├── embeddings.py    # Client embeddings
    ├── index.py         # Index vectoriel FAISS
    ├── clustering.py    # Clustering UMAP+HDBSCAN
    └── scoring.py       # Calcul proximités
```