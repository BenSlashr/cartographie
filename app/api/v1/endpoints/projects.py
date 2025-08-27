from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import List, Optional
import uuid
import json
from pathlib import Path
import pandas as pd

from app.models.schemas import (
    ProjectCreate, Project, ImportResult, AnalysisResult, 
    ClusterInfo, ProximityItem, ExportRequest
)
from app.services.ingest import IngestService
from app.services.embeddings import EmbeddingsService
from app.services.index import VectorIndexService
from app.services.clustering import ClusteringService
from app.services.scoring import ScoringService
from app.services.database import DatabaseService
from app.core.config import settings

router = APIRouter()

ingest_service = IngestService()
embeddings_service = EmbeddingsService()
index_service = VectorIndexService()
clustering_service = ClusteringService()
scoring_service = ScoringService()
db_service = DatabaseService()

projects_db = {}

@router.post("/", response_model=Project)
async def create_project(project: ProjectCreate):
    project_id = str(uuid.uuid4())
    
    # Créer en base de données
    db_project = db_service.create_project(
        project_id=project_id,
        name=project.name,
        description=project.description
    )
    
    # Maintenir compatibilité avec projects_db
    new_project = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "parameters": project.parameters,
        "created_at": db_project.created_at.isoformat(),
        "status": "created"
    }
    
    projects_db[project_id] = new_project
    
    project_dir = Path(settings.DATA_DIR) / project_id
    project_dir.mkdir(exist_ok=True)
    
    return Project(**new_project)

@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    return Project(**projects_db[project_id])

@router.get("/", response_model=List[Project])
async def list_projects():
    # Récupérer les projets depuis la base de données
    db_projects = db_service.list_projects()
    
    # Convertir en format API avec compatibilité ancienne structure
    api_projects = []
    for project in db_projects:
        # Créer/mettre à jour dans projects_db pour compatibilité
        if project.id not in projects_db:
            projects_db[project.id] = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "status": project.status,
                "parameters": {}
            }
        
        api_projects.append(Project(
            id=project.id,
            name=project.name,
            description=project.description,
            parameters={},
            created_at=project.created_at.isoformat(),
            status=project.status
        ))
    
    return api_projects

@router.post("/{project_id}/import-chunk")
async def import_chunk(
    project_id: str,
    chunk_data: UploadFile = File(..., description="Données du chunk CSV"),
    file_type: str = File(..., description="Type de fichier: pages ou links"), 
    chunk_index: int = File(..., description="Index du chunk"),
    total_chunks: int = File(..., description="Nombre total de chunks"),
    is_first_chunk: bool = File(..., description="Premier chunk"),
    is_last_chunk: bool = File(..., description="Dernier chunk")
):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Nom du fichier temporaire pour ce type
        temp_filename = f"temp_{file_type}.csv"
        temp_path = project_dir / temp_filename
        
        # Lire le contenu du chunk
        chunk_content = await chunk_data.read()
        chunk_text = chunk_content.decode('utf-8')
        
        if is_first_chunk:
            # Premier chunk : créer le fichier avec header
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(chunk_text)
            print(f"🗂️ CHUNK: Premier chunk {file_type} créé: {temp_path}")
        else:
            # Chunks suivants : append sans header
            lines = chunk_text.split('\n')
            data_lines = lines[1:]  # Supprimer header
            
            with open(temp_path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(data_lines))
            print(f"📎 CHUNK: Chunk {chunk_index + 1}/{total_chunks} ajouté à {file_type}")
        
        return {
            "project_id": project_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "file_type": file_type,
            "status": "chunk_uploaded"
        }
        
    except Exception as e:
        print(f"❌ CHUNK ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur upload chunk: {str(e)}")

@router.post("/{project_id}/import-finalize", response_model=ImportResult) 
async def finalize_import(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        temp_pages = project_dir / "temp_pages.csv"
        temp_links = project_dir / "temp_links.csv"
        
        # Traiter le fichier pages (obligatoire)
        if not temp_pages.exists():
            raise HTTPException(status_code=400, detail="Aucun fichier pages uploadé")
        
        # Renommer et traiter comme avant
        final_pages = project_dir / "pages.csv"
        temp_pages.rename(final_pages)
        
        final_links = None
        if temp_links.exists():
            final_links = project_dir / "links.csv" 
            temp_links.rename(final_links)
        
        # Traitement avec ingest_service comme avant
        result = ingest_service.process_csv(
            project_id,
            str(final_pages),
            str(final_links) if final_links else None
        )
        
        if result["valid"]:
            projects_db[project_id]["status"] = "imported"
        
        print(f"🎯 FINALIZE: Import terminé - {result['pages_rows']} pages")
        
        return ImportResult(
            project_id=project_id,
            rows=result["pages_rows"], 
            path=result["pages_path"],
            message=f"Import finalisé: {result['pages_rows']} pages"
        )
        
    except Exception as e:
        print(f"❌ FINALIZE ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur finalisation: {str(e)}")

@router.post("/{project_id}/import", response_model=ImportResult)
async def import_csv(
    project_id: str, 
    pages_file: UploadFile = File(..., description="Fichier CSV des pages"),
    edges_file: Optional[UploadFile] = File(None, description="Fichier CSV des liens (optionnel)")
):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    if not pages_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Le fichier pages doit être un CSV")
    
    if edges_file and not edges_file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Le fichier liens doit être un CSV")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Sauvegarder le fichier des pages
        pages_upload_path = project_dir / f"upload_pages_{pages_file.filename}"
        with open(pages_upload_path, "wb") as buffer:
            content = await pages_file.read()
            buffer.write(content)
        
        # Sauvegarder le fichier des liens si fourni
        edges_upload_path = None
        if edges_file:
            edges_upload_path = project_dir / f"upload_edges_{edges_file.filename}"
            with open(edges_upload_path, "wb") as buffer:
                content = await edges_file.read()
                buffer.write(content)
        
        # Traiter les fichiers
        result = ingest_service.process_csv(
            project_id, 
            str(pages_upload_path), 
            str(edges_upload_path) if edges_upload_path else None
        )
        
        if result["valid"]:
            projects_db[project_id]["status"] = "imported"
        
        return ImportResult(
            project_id=project_id,
            rows=result["pages_rows"],
            path=result["pages_path"],
            message=result["message"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")

@router.post("/{project_id}/embed")
async def generate_embeddings(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    if projects_db[project_id]["status"] != "imported":
        raise HTTPException(status_code=400, detail="Le projet doit être importé avant de générer les embeddings")
    
    try:
        result = await embeddings_service.embed_pages(project_id)
        projects_db[project_id]["status"] = "embedded"
        
        return {
            "project_id": project_id,
            "total_embeddings": result["total_embeddings"],
            "dimensions": result["dimensions"],
            "message": "Embeddings générés avec succès"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des embeddings: {str(e)}")

@router.post("/{project_id}/analyze-simple")
async def analyze_simple(project_id: str):
    """Mode simple SANS Celery - lance l'analyse en arrière plan"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    if projects_db[project_id]["status"] != "imported":
        raise HTTPException(status_code=400, detail="Le projet doit être importé")
    
    # Marquer comme en cours d'analyse
    projects_db[project_id]["status"] = "analyzing"
    projects_db[project_id]["progress"] = {
        "step": 1,
        "total_steps": 4, 
        "step_name": "Initialisation",
        "progress_percentage": 0,
        "message": "Démarrage de l'analyse..."
    }
    
    # Lancer l'analyse en arrière plan
    import asyncio
    asyncio.create_task(run_analysis_background(project_id))
    
    return {"message": "Analyse lancée", "project_id": project_id, "status": "analyzing"}

async def run_analysis_background(project_id: str):
    """Analyse en arrière plan avec mise à jour du progrès"""
    analysis = None
    try:
        print(f"🎪 BACKGROUND: Starting analysis for project {project_id}")
        
        # Créer l'analyse en base
        analysis = db_service.create_analysis(
            project_id=project_id,
            analysis_type="full",
            clustering_method="hdbscan"
        )
        print(f"🎪 BACKGROUND: Created analysis #{analysis.id}")
        
        # Mettre à jour le statut du projet
        db_service.update_project_status(project_id, "analyzing")
        
        # 1. Générer les embeddings directement
        print(f"🎪 BACKGROUND: Step 1/4 - Generating embeddings...")
        projects_db[project_id]["progress"] = {
            "step": 1,
            "total_steps": 4,
            "step_name": "Génération des embeddings",
            "progress_percentage": 0,
            "message": "Génération des embeddings en cours...",
            "analysis_id": analysis.id
        }
        
        embeddings_result = await embeddings_service.embed_pages(project_id)
        vectors = embeddings_result["vectors_array"]
        node_ids = embeddings_result["node_ids"]
        urls = embeddings_result["urls"]
        print(f"🎪 BACKGROUND: Embeddings done - {len(vectors)} vectors")
        
        # 2. Index vectoriel
        print(f"🎪 BACKGROUND: Step 2/4 - Computing similarities...")
        projects_db[project_id]["progress"] = {
            "step": 2,
            "total_steps": 4,
            "step_name": "Calcul des similarités",
            "progress_percentage": 25,
            "message": f"Calcul des similarités pour {len(vectors)} pages..."
        }
        
        semantic_neighbors = index_service.find_semantic_neighbors(vectors, node_ids)
        print(f"🎪 BACKGROUND: Similarities done")
        
        # 3. Clustering  
        print(f"🎪 BACKGROUND: Step 3/4 - Clustering...")
        projects_db[project_id]["progress"] = {
            "step": 3,
            "total_steps": 4,
            "step_name": "Clustering thématique",
            "progress_percentage": 50,
            "message": "Analyse des clusters thématiques..."
        }
        
        clustering_results = clustering_service.full_clustering_analysis(vectors, node_ids, urls)
        print(f"🎪 BACKGROUND: Clustering done - {len(clustering_results['clusters'])} clusters")
        
        # 4. Proximité
        print(f"🎪 BACKGROUND: Step 4/4 - Proximity analysis...")
        projects_db[project_id]["progress"] = {
            "step": 4,
            "total_steps": 4,
            "step_name": "Détection des anomalies",
            "progress_percentage": 75,
            "message": "Détection des anomalies de proximité..."
        }
        
        proximity_analysis = scoring_service.full_proximity_analysis(
            project_id, vectors, node_ids, urls, semantic_neighbors, clustering_results["clusters"]
        )
        print(f"🎪 BACKGROUND: Proximity done - {len(proximity_analysis['proximity_anomalies'])} anomalies")
        
        # Résultat final
        final_result = {
            "project_id": project_id,
            "total_pages": len(node_ids),
            "total_embeddings": len(vectors),
            "dimensions": embeddings_result.get("dimensions", 384),
            "clusters": clustering_results["clusters"],
            "proximities": proximity_analysis["proximity_anomalies"],
            "projection_2d": clustering_results["projection_2d"],
            "summary": proximity_analysis.get("summary", {}),
            "embeddings_path": embeddings_result.get("embeddings_path"),
            "clustering_results_path": clustering_service.save_clustering_results(project_id, clustering_results)
        }
        
        # Sauvegarder en base de données
        db_service.update_analysis_results(
            analysis.id,
            final_result,
            status="completed"
        )
        
        # Mettre à jour le statut du projet
        db_service.update_project_status(project_id, "analyzed")
        
        # Sauvegarder les résultats (ancien format pour compatibilité)
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        with open(results_path, 'w') as f:
            import json
            json.dump(final_result, f, indent=2, default=str)
        
        projects_db[project_id]["status"] = "analyzed"
        projects_db[project_id]["progress"] = {
            "step": 4,
            "total_steps": 4,
            "step_name": "Analyse terminée",
            "progress_percentage": 100,
            "message": f"Analyse terminée : {len(node_ids)} pages, {len(clustering_results['clusters'])} clusters, {len(proximity_analysis['proximity_anomalies'])} anomalies",
            "analysis_id": analysis.id
        }
        projects_db[project_id]["results"] = final_result
        
        print(f"🎪 BACKGROUND: Analysis completed for project {project_id} (analysis #{analysis.id})")
        
    except Exception as e:
        print(f"🎪 BACKGROUND ERROR: {type(e).__name__}: {str(e)}")
        
        # Mettre à jour l'analyse en cas d'erreur
        if analysis:
            db_service.update_analysis_results(
                analysis.id,
                {},
                status="failed",
                error_message=str(e)
            )
            db_service.update_project_status(project_id, "error")
        
        projects_db[project_id]["status"] = "error"
        projects_db[project_id]["progress"] = {
            "step": 0,
            "total_steps": 4,
            "step_name": "Erreur",
            "progress_percentage": 0,
            "message": f"Erreur lors de l'analyse: {str(e)}"
        }

@router.get("/{project_id}/progress")
async def get_analysis_progress(project_id: str):
    """Récupère le progrès de l'analyse"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    project = projects_db[project_id]
    status = project["status"]
    progress = project.get("progress", {})
    
    if status == "analyzed":
        # Si l'analyse est terminée, renvoyer les résultats
        results = project.get("results")
        if results:
            return {
                "status": "SUCCESS",
                "progress": progress,
                "result": results
            }
        else:
            # Charger les résultats depuis le fichier
            project_dir = Path(settings.DATA_DIR) / project_id
            results_path = project_dir / "analysis_results.json"
            if results_path.exists():
                import json
                with open(results_path, 'r') as f:
                    results = json.load(f)
                return {
                    "status": "SUCCESS",
                    "progress": progress,
                    "result": results
                }
    
    return {
        "status": status.upper(),
        "progress": progress
    }

@router.get("/{project_id}/mock-results")
async def get_mock_results(project_id: str):
    """Données mock pour tester l'interface graphique"""
    import random
    import numpy as np
    
    # Générer des données mock cohérentes
    np.random.seed(42)
    random.seed(42)
    
    # 50 pages avec des URLs réalistes
    urls = [
        "https://example.com/accueil",
        "https://example.com/produits",
        "https://example.com/services",
        "https://example.com/a-propos",
        "https://example.com/contact",
        "https://example.com/blog",
        "https://example.com/actualites",
        "https://example.com/FAQ",
        "https://example.com/support",
        "https://example.com/documentation",
        "https://example.com/produits/categorie-1",
        "https://example.com/produits/categorie-2",
        "https://example.com/produits/categorie-3",
        "https://example.com/produits/article-1",
        "https://example.com/produits/article-2",
        "https://example.com/produits/article-3",
        "https://example.com/produits/article-4",
        "https://example.com/produits/article-5",
        "https://example.com/blog/post-1",
        "https://example.com/blog/post-2",
        "https://example.com/blog/post-3",
        "https://example.com/blog/post-4",
        "https://example.com/blog/post-5",
        "https://example.com/services/consultation",
        "https://example.com/services/formation",
        "https://example.com/services/support-technique",
        "https://example.com/services/maintenance",
        "https://example.com/entreprise/histoire",
        "https://example.com/entreprise/equipe",
        "https://example.com/entreprise/valeurs",
        "https://example.com/entreprise/carrieres",
        "https://example.com/actualites/communique-1",
        "https://example.com/actualites/communique-2",
        "https://example.com/actualites/evenement-1",
        "https://example.com/actualites/evenement-2",
        "https://example.com/ressources/guides",
        "https://example.com/ressources/tutoriels",
        "https://example.com/ressources/webinaires",
        "https://example.com/ressources/etudes-cas",
        "https://example.com/partenaires",
        "https://example.com/tarifs",
        "https://example.com/mentions-legales",
        "https://example.com/politique-confidentialite",
        "https://example.com/conditions-utilisation",
        "https://example.com/plan-site",
        "https://example.com/newsletter",
        "https://example.com/temoignages",
        "https://example.com/references",
        "https://example.com/certifications",
        "https://example.com/partenariats"
    ]
    
    # Clusters thématiques cohérents
    clusters = [
        {
            "cluster_id": 0,
            "size": 18,
            "theme": "Produits et Services",
            "urls": urls[:18],
            "centroid": [0.2, 0.8]  # Position dans la projection 2D
        },
        {
            "cluster_id": 1, 
            "size": 12,
            "theme": "Contenu Editorial",
            "urls": urls[18:30],
            "centroid": [-0.3, 0.1]
        },
        {
            "cluster_id": 2,
            "size": 10,
            "theme": "Entreprise et À Propos", 
            "urls": urls[30:40],
            "centroid": [0.5, -0.4]
        },
        {
            "cluster_id": 3,
            "size": 10,
            "theme": "Ressources et Support",
            "urls": urls[40:50],
            "centroid": [-0.6, -0.2]
        }
    ]
    
    # Projection 2D avec dispersion réaliste
    projection_2d = []
    for i, url in enumerate(urls):
        cluster_id = 0 if i < 18 else 1 if i < 30 else 2 if i < 40 else 3
        cluster = clusters[cluster_id]
        
        # Position basée sur le centroid du cluster + bruit
        x = cluster["centroid"][0] + np.random.normal(0, 0.2)
        y = cluster["centroid"][1] + np.random.normal(0, 0.2) 
        
        projection_2d.append({
            "url": url,
            "x": float(x),
            "y": float(y),
            "cluster": cluster_id
        })
    
    # Anomalies de proximité (pages sémantiquement proches mais éloignées en liens)
    proximities = [
        {
            "node_i": "node-1",
            "node_j": "node-15", 
            "url_i": "https://example.com/produits/article-1",
            "url_j": "https://example.com/produits/article-5",
            "cosine": 0.92,
            "hops": 5,
            "anomaly_score": 0.85
        },
        {
            "node_i": "node-19",
            "node_j": "node-23",
            "url_i": "https://example.com/blog/post-1", 
            "url_j": "https://example.com/blog/post-5",
            "cosine": 0.89,
            "hops": 4,
            "anomaly_score": 0.78
        },
        {
            "node_i": "node-2",
            "node_j": "node-40",
            "url_i": "https://example.com/services",
            "url_j": "https://example.com/partenaires",
            "cosine": 0.86,
            "hops": 6,
            "anomaly_score": 0.72
        },
        {
            "node_i": "node-36",
            "node_j": "node-48",
            "url_i": "https://example.com/ressources/guides",
            "url_j": "https://example.com/references", 
            "cosine": 0.84,
            "hops": 3,
            "anomaly_score": 0.69
        },
        {
            "node_i": "node-11",
            "node_j": "node-24",
            "url_i": "https://example.com/produits/categorie-1",
            "url_j": "https://example.com/services/consultation",
            "cosine": 0.81,
            "hops": 7,
            "anomaly_score": 0.66
        }
    ]
    
    # Statistiques du graphe
    summary = {
        "graph_stats": {
            "total_nodes": 50,
            "total_edges": 127,
            "avg_degree": 2.54,
            "diameter": 8,
            "clustering_coefficient": 0.34
        },
        "semantic_stats": {
            "avg_cosine_similarity": 0.42,
            "min_similarity": 0.08,
            "max_similarity": 0.96
        }
    }
    
    return {
        "project_id": project_id,
        "total_pages": 50,
        "clusters": clusters,
        "proximities": proximities,
        "projection_2d": projection_2d,
        "summary": summary
    }

@router.post("/{project_id}/analyze-sync")
async def analyze_project_sync(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    if projects_db[project_id]["status"] != "embedded":
        raise HTTPException(status_code=400, detail="Les embeddings doivent être générés avant l'analyse")
    
    try:
        embeddings_data = embeddings_service.load_embeddings(project_id)
        vectors = embeddings_data["vectors_array"]
        node_ids = embeddings_data["node_ids"]
        urls = embeddings_data["urls"]
        
        semantic_neighbors = index_service.find_semantic_neighbors(vectors, node_ids)
        
        clustering_results = clustering_service.full_clustering_analysis(
            vectors, node_ids, urls
        )
        
        proximity_analysis = scoring_service.full_proximity_analysis(
            project_id, vectors, node_ids, urls, semantic_neighbors, clustering_results["clusters"]
        )
        
        clusters = [
            ClusterInfo(
                cluster_id=c["cluster_id"],
                size=c["size"],
                centroid=c["centroid"],
                urls=c["urls"],
                theme=c["theme"]
            ) for c in clustering_results["clusters"]
        ]
        
        proximities = [
            ProximityItem(
                node_i=p["node_i"],
                node_j=p["node_j"],
                url_i=p["url_i"],
                url_j=p["url_j"],
                cosine=p["cosine"],
                hops=p["hops"],
                anomaly_score=p["anomaly_score"]
            ) for p in proximity_analysis["proximity_anomalies"]
        ]
        
        analysis_result = {
            "project_id": project_id,
            "total_pages": len(node_ids),
            "clusters": clusters,
            "proximities": proximities,
            "projection_2d": clustering_results["projection_2d"]
        }
        
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        with open(results_path, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        projects_db[project_id]["status"] = "analyzed"
        
        return AnalysisResult(**analysis_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

@router.get("/{project_id}/clusters", response_model=List[ClusterInfo])
async def get_clusters(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Résultats d'analyse non trouvés")
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        return [ClusterInfo(**cluster) for cluster in results["clusters"]]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/{project_id}/proximities", response_model=List[ProximityItem])
async def get_proximities(
    project_id: str,
    min_sim: Optional[float] = Query(None, ge=0, le=1),
    min_hops: Optional[int] = Query(None, ge=0)
):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Résultats d'analyse non trouvés")
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        proximities = [ProximityItem(**p) for p in results["proximities"]]
        
        if min_sim is not None:
            proximities = [p for p in proximities if p.cosine >= min_sim]
        
        if min_hops is not None:
            proximities = [p for p in proximities if p.hops is not None and p.hops >= min_hops]
        
        return proximities
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/{project_id}/export/{format}")
async def export_results(project_id: str, format: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    if format not in ["csv", "json", "parquet"]:
        raise HTTPException(status_code=400, detail="Format non supporté")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        
        if not results_path.exists():
            raise HTTPException(status_code=404, detail="Résultats d'analyse non trouvés")
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        if format == "csv":
            df = pd.DataFrame(results["proximities"])
            export_path = project_dir / f"export_proximities.csv"
            df.to_csv(export_path, index=False)
        elif format == "json":
            export_path = results_path
        elif format == "parquet":
            df = pd.DataFrame(results["proximities"])
            export_path = project_dir / f"export_proximities.parquet"
            df.to_parquet(export_path)
        
        return FileResponse(export_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")

@router.get("/{project_id}/preview")
async def get_preview(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    try:
        project_dir = Path(settings.DATA_DIR) / project_id
        results_path = project_dir / "analysis_results.json"
        
        if results_path.exists():
            with open(results_path, 'r') as f:
                results = json.load(f)
            
            return {
                "project_id": project_id,
                "status": projects_db[project_id]["status"],
                "total_pages": results.get("total_pages", 0),
                "total_clusters": len(results.get("clusters", [])),
                "total_proximities": len(results.get("proximities", [])),
                "projection_2d": results.get("projection_2d", [])[:100]  # Limité pour la preview
            }
        else:
            return {
                "project_id": project_id,
                "status": projects_db[project_id]["status"],
                "message": "Analyse non encore effectuée"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# Nouveaux endpoints pour la gestion de la base de données

@router.get("/database/projects")
async def list_database_projects():
    """Liste tous les projets avec leurs analyses depuis la base"""
    projects = db_service.list_projects()
    result = []
    
    for project in projects:
        latest_analysis = db_service.get_latest_analysis(project.id)
        result.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "total_pages": project.total_pages,
            "total_links": project.total_links,
            "latest_analysis": {
                "id": latest_analysis.id,
                "created_at": latest_analysis.created_at.isoformat(),
                "status": latest_analysis.status,
                "total_clusters": latest_analysis.total_clusters,
                "total_anomalies": latest_analysis.total_anomalies,
                "clustering_method": latest_analysis.clustering_method
            } if latest_analysis else None
        })
    
    return result

@router.get("/{project_id}/analyses")
async def list_project_analyses(project_id: str):
    """Liste toutes les analyses d'un projet"""
    analyses = db_service.list_analyses(project_id)
    
    return [{
        "id": analysis.id,
        "created_at": analysis.created_at.isoformat(),
        "analysis_type": analysis.analysis_type,
        "status": analysis.status,
        "embedding_model": analysis.embedding_model,
        "clustering_method": analysis.clustering_method,
        "min_cluster_size": analysis.min_cluster_size,
        "total_embeddings": analysis.total_embeddings,
        "embedding_dimensions": analysis.embedding_dimensions,
        "total_clusters": analysis.total_clusters,
        "total_anomalies": analysis.total_anomalies,
        "error_message": analysis.error_message
    } for analysis in analyses]

@router.get("/{project_id}/analyses/{analysis_id}")
async def get_analysis_results(project_id: str, analysis_id: int):
    """Récupère les résultats complets d'une analyse"""
    analysis = db_service.get_analysis(analysis_id)
    
    if not analysis or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    
    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail=f"Analyse non terminée (statut: {analysis.status})")
    
    # Charger l'analyse dans projects_db pour compatibilité avec l'interface
    projects_db[project_id] = {
        "id": project_id,
        "status": "analyzed",
        "results": {
            "project_id": project_id,
            "clusters": analysis.clusters_data or [],
            "proximities": analysis.anomalies_data or [],
            "projection_2d": analysis.projection_data or []
        }
    }
    
    return {
        "analysis": {
            "id": analysis.id,
            "created_at": analysis.created_at.isoformat(),
            "status": analysis.status,
            "total_embeddings": analysis.total_embeddings,
            "embedding_dimensions": analysis.embedding_dimensions,
            "total_clusters": analysis.total_clusters,
            "total_anomalies": analysis.total_anomalies
        },
        "results": {
            "clusters": analysis.clusters_data or [],
            "anomalies": analysis.anomalies_data or [],
            "projection_2d": analysis.projection_data or []
        }
    }

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Supprimer un projet et toutes ses analyses"""
    success = db_service.delete_project(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    # Nettoyer projects_db
    if project_id in projects_db:
        del projects_db[project_id]
    
    # Supprimer les fichiers
    project_dir = Path(settings.DATA_DIR) / project_id
    if project_dir.exists():
        import shutil
        shutil.rmtree(project_dir)
    
    return {"message": "Projet supprimé avec succès"}