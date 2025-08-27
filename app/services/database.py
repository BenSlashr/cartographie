from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.database import Project, Analysis, get_db_session, create_tables
from datetime import datetime
import json

class DatabaseService:
    def __init__(self):
        # Créer les tables si elles n'existent pas
        create_tables()
    
    def create_project(
        self, 
        project_id: str, 
        name: str, 
        description: str = None,
        total_pages: int = 0,
        total_links: int = 0
    ) -> Project:
        """Créer un nouveau projet"""
        db = get_db_session()
        try:
            project = Project(
                id=project_id,
                name=name,
                description=description,
                total_pages=total_pages,
                total_links=total_links,
                status="created"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            return project
        finally:
            db.close()
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Récupérer un projet par son ID"""
        db = get_db_session()
        try:
            return db.query(Project).filter(Project.id == project_id).first()
        finally:
            db.close()
    
    def list_projects(self) -> List[Project]:
        """Lister tous les projets"""
        db = get_db_session()
        try:
            return db.query(Project).order_by(Project.updated_at.desc()).all()
        finally:
            db.close()
    
    def update_project_status(self, project_id: str, status: str):
        """Mettre à jour le statut d'un projet"""
        db = get_db_session()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = status
                project.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    
    def create_analysis(
        self,
        project_id: str,
        analysis_type: str = "full",
        embedding_model: str = "BAAI/bge-m3",
        clustering_method: str = "hdbscan",
        min_cluster_size: int = 10
    ) -> Analysis:
        """Créer une nouvelle analyse"""
        db = get_db_session()
        try:
            analysis = Analysis(
                project_id=project_id,
                analysis_type=analysis_type,
                embedding_model=embedding_model,
                clustering_method=clustering_method,
                min_cluster_size=min_cluster_size,
                status="pending"
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            return analysis
        finally:
            db.close()
    
    def get_analysis(self, analysis_id: int) -> Optional[Analysis]:
        """Récupérer une analyse par son ID"""
        db = get_db_session()
        try:
            return db.query(Analysis).filter(Analysis.id == analysis_id).first()
        finally:
            db.close()
    
    def get_latest_analysis(self, project_id: str) -> Optional[Analysis]:
        """Récupérer la dernière analyse d'un projet"""
        db = get_db_session()
        try:
            return db.query(Analysis).filter(
                Analysis.project_id == project_id
            ).order_by(Analysis.created_at.desc()).first()
        finally:
            db.close()
    
    def list_analyses(self, project_id: str = None) -> List[Analysis]:
        """Lister les analyses (optionnel: pour un projet spécifique)"""
        db = get_db_session()
        try:
            query = db.query(Analysis)
            if project_id:
                query = query.filter(Analysis.project_id == project_id)
            return query.order_by(Analysis.created_at.desc()).all()
        finally:
            db.close()
    
    def update_analysis_results(
        self,
        analysis_id: int,
        results: Dict[str, Any],
        status: str = "completed",
        error_message: str = None
    ):
        """Mettre à jour les résultats d'une analyse"""
        db = get_db_session()
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                # Extraire les métadonnées des résultats
                if "total_embeddings" in results:
                    analysis.total_embeddings = results["total_embeddings"]
                if "dimensions" in results:
                    analysis.embedding_dimensions = results["dimensions"]
                if "clusters" in results:
                    analysis.total_clusters = len(results["clusters"])
                    analysis.clusters_data = results["clusters"]
                if "projection_2d" in results:
                    analysis.projection_data = results["projection_2d"]
                if "anomalies" in results:
                    analysis.total_anomalies = len(results["anomalies"])
                    analysis.anomalies_data = results["anomalies"]
                
                # Chemins des fichiers
                if "embeddings_path" in results:
                    analysis.embeddings_path = results["embeddings_path"]
                if "faiss_index_path" in results:
                    analysis.faiss_index_path = results["faiss_index_path"]
                if "clustering_results_path" in results:
                    analysis.clustering_results_path = results["clustering_results_path"]
                
                analysis.status = status
                analysis.error_message = error_message
                db.commit()
        finally:
            db.close()
    
    def get_project_with_latest_analysis(self, project_id: str) -> Dict[str, Any]:
        """Récupérer un projet avec sa dernière analyse"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        latest_analysis = self.get_latest_analysis(project_id)
        
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "total_pages": project.total_pages,
                "total_links": project.total_links,
                "status": project.status
            },
            "latest_analysis": {
                "id": latest_analysis.id,
                "created_at": latest_analysis.created_at.isoformat(),
                "analysis_type": latest_analysis.analysis_type,
                "embedding_model": latest_analysis.embedding_model,
                "clustering_method": latest_analysis.clustering_method,
                "min_cluster_size": latest_analysis.min_cluster_size,
                "total_embeddings": latest_analysis.total_embeddings,
                "embedding_dimensions": latest_analysis.embedding_dimensions,
                "total_clusters": latest_analysis.total_clusters,
                "total_anomalies": latest_analysis.total_anomalies,
                "status": latest_analysis.status,
                "error_message": latest_analysis.error_message,
                "clusters_data": latest_analysis.clusters_data,
                "projection_data": latest_analysis.projection_data,
                "anomalies_data": latest_analysis.anomalies_data
            } if latest_analysis else None
        }
    
    def delete_project(self, project_id: str) -> bool:
        """Supprimer un projet et toutes ses analyses"""
        db = get_db_session()
        try:
            # Supprimer toutes les analyses du projet
            db.query(Analysis).filter(Analysis.project_id == project_id).delete()
            
            # Supprimer le projet
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                db.delete(project)
                db.commit()
                return True
            return False
        finally:
            db.close()