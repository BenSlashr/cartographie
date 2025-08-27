import pandas as pd
import uuid
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse
from app.core.config import settings

class IngestService:
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
    
    def validate_pages_csv(self, file_path: str) -> Dict[str, Any]:
        try:
            # Try comma first, then semicolon
            try:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
            
            # Support des différents formats de colonnes
            url_columns = ["url", "Adresse", "URL"]
            content_columns = ["contenu", "Title 1", "Meta Description 1", "H1-1", "content"]
            
            url_col = None
            content_col = None
            
            # Trouver la colonne URL
            for col in url_columns:
                if col in df.columns:
                    url_col = col
                    break
            
            if not url_col:
                raise ValueError(f"Aucune colonne URL trouvée. Colonnes disponibles: {list(df.columns)}")
            
            # Construire le contenu à partir de plusieurs colonnes si nécessaire
            if "contenu" in df.columns:
                content_col = "contenu"
            else:
                # Combiner Title, Meta Description et H1 pour créer le contenu
                content_parts = []
                for col in ["Title 1", "Meta Description 1", "H1-1"]:
                    if col in df.columns:
                        content_parts.append(col)
                
                if content_parts:
                    df["contenu"] = df[content_parts].fillna("").agg(" ".join, axis=1)
                    content_col = "contenu"
                else:
                    raise ValueError("Aucune colonne de contenu trouvée")
            
            # Nettoyer les données
            df = df.dropna(subset=[url_col])
            df["url"] = df[url_col]  # Normaliser le nom de colonne
            
            valid_urls = []
            for idx, row in df.iterrows():
                try:
                    url = str(row["url"]).strip()
                    if url.startswith('http'):
                        parsed = urlparse(url)
                        if parsed.scheme and parsed.netloc:
                            valid_urls.append(idx)
                except:
                    continue
            
            df = df.iloc[valid_urls]
            
            if df.empty:
                raise ValueError("Aucune URL valide trouvée")
            
            df["contenu"] = df["contenu"].fillna("")
            
            return {
                "valid": True,
                "rows": len(df),
                "dataframe": df,
                "message": f"Validation réussie: {len(df)} lignes valides"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "rows": 0,
                "dataframe": None,
                "message": f"Erreur de validation: {str(e)}"
            }
    
    def validate_edges_csv(self, file_path: str) -> Dict[str, Any]:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
            
            # Support des différents formats de colonnes pour les liens
            source_columns = ["source", "Source", "from", "url_source"]
            dest_columns = ["destination", "Destination", "target", "to", "url_dest"]
            
            source_col = None
            dest_col = None
            
            # Trouver les colonnes source et destination
            for col in source_columns:
                if col in df.columns:
                    source_col = col
                    break
            
            for col in dest_columns:
                if col in df.columns:
                    dest_col = col
                    break
            
            if not source_col or not dest_col:
                raise ValueError(f"Colonnes source/destination non trouvées. Disponibles: {list(df.columns)}")
            
            # Normaliser les noms de colonnes
            df["source"] = df[source_col].astype(str)
            df["destination"] = df[dest_col].astype(str)
            
            # Filtrer les liens internes valides
            valid_links = []
            for idx, row in df.iterrows():
                try:
                    source = str(row["source"]).strip()
                    dest = str(row["destination"]).strip()
                    
                    if (source.startswith('http') and dest.startswith('http') and 
                        source != dest):  # Éviter les self-links
                        valid_links.append(idx)
                except:
                    continue
            
            df = df.iloc[valid_links]
            
            return {
                "valid": True,
                "rows": len(df),
                "dataframe": df,
                "message": f"Validation réussie: {len(df)} liens valides"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "rows": 0,
                "dataframe": None,
                "message": f"Erreur de validation liens: {str(e)}"
            }

    def process_csv(self, project_id: str, pages_path: str, edges_path: str = None) -> Dict[str, Any]:
        validation_result = self.validate_pages_csv(pages_path)
        
        if not validation_result["valid"]:
            return validation_result
        
        pages_df = validation_result["dataframe"]
        pages_df["node_id"] = pages_df["url"].apply(lambda x: str(uuid.uuid5(uuid.NAMESPACE_URL, x)))
        
        project_dir = self.data_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Sauvegarder les pages
        pages_processed_path = project_dir / "pages.csv"
        pages_df[["url", "contenu", "node_id"]].to_csv(pages_processed_path, index=False)
        
        result = {
            "valid": True,
            "pages_rows": len(pages_df),
            "pages_path": str(pages_processed_path),
            "edges_rows": 0,
            "edges_path": None,
            "message": f"CSV traité avec succès: {len(pages_df)} pages"
        }
        
        # Traiter les liens si fournis
        if edges_path:
            edges_validation = self.validate_edges_csv(edges_path)
            if edges_validation["valid"]:
                edges_df = edges_validation["dataframe"]
                
                # Filtrer les liens pour ne garder que ceux entre pages de notre dataset
                pages_urls = set(pages_df["url"])
                filtered_edges = []
                
                for _, row in edges_df.iterrows():
                    source = str(row["source"]).strip()
                    dest = str(row["destination"]).strip()
                    
                    if source in pages_urls and dest in pages_urls:
                        filtered_edges.append({
                            "source": source,
                            "target": dest
                        })
                
                if filtered_edges:
                    edges_final_df = pd.DataFrame(filtered_edges)
                    edges_processed_path = project_dir / "edges.csv"
                    edges_final_df.to_csv(edges_processed_path, index=False)
                    
                    result.update({
                        "edges_rows": len(edges_final_df),
                        "edges_path": str(edges_processed_path),
                        "message": f"CSV traité avec succès: {len(pages_df)} pages, {len(edges_final_df)} liens internes"
                    })
        
        return result
    
    def get_pages(self, project_id: str) -> pd.DataFrame:
        project_dir = self.data_dir / project_id
        pages_path = project_dir / "pages.csv"
        
        if not pages_path.exists():
            raise FileNotFoundError(f"Fichier pages.csv non trouvé pour le projet {project_id}")
        
        return pd.read_csv(pages_path)