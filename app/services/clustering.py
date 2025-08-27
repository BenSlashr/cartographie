import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import umap
import hdbscan
from app.core.config import settings

class ClusteringService:
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
    
    def reduce_dimensions_umap(
        self, 
        vectors: np.ndarray, 
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        n_components: int = 50,
        random_state: int = 42
    ) -> np.ndarray:
        n_samples = len(vectors)
        n_neighbors = min(n_neighbors, n_samples - 1)
        n_components = min(n_components, n_samples - 1)
        
        if n_neighbors < 2:
            n_neighbors = 2
        if n_components < 2:
            n_components = 2
            
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            random_state=random_state,
            metric='cosine'
        )
        
        return reducer.fit_transform(vectors)
    
    def cluster_hdbscan(
        self,
        reduced_vectors: np.ndarray,
        min_cluster_size: int = 10,  # Augmenté de 5 à 10 pour moins de clusters
        min_samples: Optional[int] = None,
        cluster_selection_epsilon: float = 0.2  # Nouveau paramètre pour fusionner clusters proches
    ) -> np.ndarray:
        n_samples = len(reduced_vectors)
        min_cluster_size = min(min_cluster_size, max(3, n_samples // 3))  # Plus conservateur
        
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            metric='euclidean'
        )
        
        cluster_labels = clusterer.fit_predict(reduced_vectors)
        return cluster_labels
    
    def cluster_kmeans(
        self,
        vectors: np.ndarray,
        n_clusters: int = 10,
        random_state: int = 42
    ) -> np.ndarray:
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=10
        )
        
        cluster_labels = kmeans.fit_predict(vectors)
        return cluster_labels
    
    def project_2d(
        self,
        vectors: np.ndarray,
        method: str = "umap",
        random_state: int = 42
    ) -> np.ndarray:
        n_samples = len(vectors)
        
        if method == "umap":
            n_neighbors = min(15, n_samples - 1)
            if n_neighbors < 2:
                n_neighbors = 2
                
            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                min_dist=0.1,
                n_components=2,
                random_state=random_state,
                metric='cosine'
            )
        elif method == "pca":
            reducer = PCA(n_components=min(2, n_samples - 1), random_state=random_state)
        else:
            raise ValueError(f"Méthode non supportée: {method}")
        
        return reducer.fit_transform(vectors)
    
    def analyze_clusters(
        self,
        vectors: np.ndarray,
        node_ids: List[str],
        urls: List[str],
        cluster_labels: np.ndarray,
        min_size_threshold: int = 3  # Nouveau: seuil minimum de taille
    ) -> List[Dict[str, Any]]:
        clusters = []
        unique_labels = np.unique(cluster_labels)
        
        for label in unique_labels:
            if label == -1:  # HDBSCAN noise
                continue
            
            mask = cluster_labels == label
            cluster_size = int(np.sum(mask))
            
            # Filtrer les clusters trop petits
            if cluster_size < min_size_threshold:
                continue
            
            cluster_vectors = vectors[mask]
            cluster_node_ids = [node_ids[i] for i in range(len(node_ids)) if mask[i]]
            cluster_urls = [urls[i] for i in range(len(urls)) if mask[i]]
            
            centroid = np.mean(cluster_vectors, axis=0)
            
            clusters.append({
                "cluster_id": int(label),
                "size": cluster_size,
                "centroid": centroid.tolist(),
                "urls": cluster_urls,
                "node_ids": cluster_node_ids,
                "theme": None  # À implémenter plus tard
            })
        
        # Trier par taille décroissante pour affichage prioritaire
        clusters.sort(key=lambda x: x["size"], reverse=True)
        
        return clusters
    
    def full_clustering_analysis(
        self,
        vectors: np.ndarray,
        node_ids: List[str],
        urls: List[str],
        clustering_method: str = "auto",
        n_clusters: Optional[int] = None
    ) -> Dict[str, Any]:
        n_samples = len(vectors)
        
        # Pour les petits datasets, utiliser K-means
        if clustering_method == "auto":
            clustering_method = "kmeans" if n_samples < 10 else "hdbscan"
        
        if clustering_method == "hdbscan" and n_samples >= 10:
            try:
                reduced_vectors = self.reduce_dimensions_umap(vectors)
                # Paramètres ajustés pour moins de clusters
                cluster_labels = self.cluster_hdbscan(
                    reduced_vectors,
                    min_cluster_size=max(10, n_samples // 15),  # Taille min adaptée
                    cluster_selection_epsilon=0.3  # Plus de fusion
                )
            except Exception as e:
                print(f"HDBSCAN failed, falling back to K-means: {e}")
                clustering_method = "kmeans"
        
        if clustering_method == "kmeans":
            if n_clusters is None:
                n_clusters = min(3, max(2, n_samples // 2))  # Heuristique plus conservative
            cluster_labels = self.cluster_kmeans(vectors, n_clusters=n_clusters)
        
        # Appliquer le seuil de taille minimum
        min_size_threshold = max(3, n_samples // 20)  # Au moins 5% des données par cluster
        clusters = self.analyze_clusters(
            vectors, node_ids, urls, cluster_labels, min_size_threshold
        )
        
        # Projection 2D avec gestion des petits datasets
        try:
            projection_2d = self.project_2d(vectors, method="umap")
        except Exception as e:
            print(f"UMAP failed, falling back to PCA: {e}")
            projection_2d = self.project_2d(vectors, method="pca")
        
        projection_data = []
        for i, (node_id, url) in enumerate(zip(node_ids, urls)):
            projection_data.append({
                "node_id": node_id,
                "url": url,
                "x": float(projection_2d[i, 0]),
                "y": float(projection_2d[i, 1]),
                "cluster": int(cluster_labels[i]) if cluster_labels[i] != -1 else None
            })
        
        return {
            "clusters": clusters,
            "cluster_labels": cluster_labels,
            "projection_2d": projection_data,
            "n_clusters": len([c for c in clusters if c["cluster_id"] != -1]),
            "noise_points": int(np.sum(cluster_labels == -1)),
            "method_used": clustering_method
        }
    
    def save_clustering_results(self, project_id: str, results: Dict[str, Any]) -> str:
        project_dir = self.data_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        results_path = project_dir / "clustering_results.json"
        
        import json
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return str(results_path)