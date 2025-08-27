from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pathlib import Path
from app.core.config import settings

# Configuration SQLite
DATABASE_URL = f"sqlite:///{settings.DATA_DIR}/cartographie.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Métadonnées du projet
    total_pages = Column(Integer, default=0)
    total_links = Column(Integer, default=0)
    
    # Status
    status = Column(String, default="created")  # created, analyzing, analyzed, error
    
class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False)
    
    # Métadonnées de l'analyse
    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_type = Column(String, default="full")  # full, embedding_only, clustering_only
    
    # Paramètres utilisés
    embedding_model = Column(String, default="BAAI/bge-m3")
    clustering_method = Column(String, default="hdbscan")
    min_cluster_size = Column(Integer, default=10)
    
    # Résultats
    total_embeddings = Column(Integer, default=0)
    embedding_dimensions = Column(Integer, default=384)
    total_clusters = Column(Integer, default=0)
    total_anomalies = Column(Integer, default=0)
    
    # Données complètes (JSON)
    clusters_data = Column(JSON, nullable=True)
    projection_data = Column(JSON, nullable=True)
    anomalies_data = Column(JSON, nullable=True)
    
    # Status et erreurs
    status = Column(String, default="pending")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Chemins des fichiers
    embeddings_path = Column(String, nullable=True)
    faiss_index_path = Column(String, nullable=True)
    clustering_results_path = Column(String, nullable=True)

def create_tables():
    """Créer toutes les tables"""
    # Assurer que le dossier data existe
    data_dir = Path(settings.DATA_DIR)
    data_dir.mkdir(exist_ok=True)
    
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """Obtenir une session de base de données directement"""
    return SessionLocal()