import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import deque
from app.core.config import settings

class ScoringService:
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
        self.dmax = settings.DMAX
        self.sim_threshold = settings.SIM_THRESHOLD
        self.hops_threshold = settings.HOPS_THRESHOLD
    
    def load_edges_data(self, project_id: str) -> Optional[pd.DataFrame]:
        project_dir = self.data_dir / project_id
        edges_path = project_dir / "edges.csv"
        
        if edges_path.exists():
            return pd.read_csv(edges_path)
        return None

    def build_link_graph(self, project_id: str = None, edges_data: Optional[List[Dict[str, str]]] = None) -> Dict[str, Set[str]]:
        graph = {}
        
        # Charger les données depuis le fichier si project_id fourni
        if project_id and not edges_data:
            edges_df = self.load_edges_data(project_id)
            if edges_df is not None:
                edges_data = edges_df.to_dict('records')
        
        if edges_data:
            for edge in edges_data:
                source = edge.get("source", "")
                target = edge.get("target", "")
                
                if source and target:
                    if source not in graph:
                        graph[source] = set()
                    graph[source].add(target)
        
        return graph
    
    def calculate_link_distance(
        self, 
        graph: Dict[str, Set[str]], 
        source: str, 
        target: str,
        max_hops: Optional[int] = None
    ) -> Optional[int]:
        if max_hops is None:
            max_hops = self.dmax
        
        if source == target:
            return 0
        
        if source not in graph:
            return None
        
        visited = {source}
        queue = deque([(source, 0)])
        
        while queue:
            current, distance = queue.popleft()
            
            if distance >= max_hops:
                continue
            
            if current in graph:
                for neighbor in graph[current]:
                    if neighbor == target:
                        return distance + 1
                    
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, distance + 1))
        
        return None
    
    def anomaly_score(self, cosine: float, hops: Optional[int]) -> float:
        if hops is None:
            return 0.0
        
        d_norm = min(hops, self.dmax) / self.dmax
        return cosine * d_norm
    
    def find_proximity_anomalies(
        self,
        vectors: np.ndarray,
        node_ids: List[str],
        urls: List[str],
        semantic_neighbors: List[Dict[str, Any]],
        graph: Optional[Dict[str, Set[str]]] = None
    ) -> List[Dict[str, Any]]:
        proximity_items = []
        
        node_to_url = dict(zip(node_ids, urls))
        
        for neighbor in semantic_neighbors:
            node_i = neighbor["node_i"]
            node_j = neighbor["node_j"]
            cosine_sim = neighbor["similarity"]
            
            if cosine_sim < self.sim_threshold:
                continue
            
            url_i = node_to_url.get(node_i)
            url_j = node_to_url.get(node_j)
            
            if not url_i or not url_j:
                continue
            
            hops = None
            if graph:
                hops = self.calculate_link_distance(graph, url_i, url_j)
                
                if hops is not None and hops < self.hops_threshold:
                    continue
            
            anomaly = self.anomaly_score(cosine_sim, hops)
            
            proximity_items.append({
                "node_i": node_i,
                "node_j": node_j,
                "url_i": url_i,
                "url_j": url_j,
                "cosine": cosine_sim,
                "hops": hops,
                "anomaly_score": anomaly
            })
        
        proximity_items.sort(key=lambda x: x["anomaly_score"], reverse=True)
        
        return proximity_items
    
    def calculate_cluster_coherence(
        self,
        clusters: List[Dict[str, Any]],
        graph: Optional[Dict[str, Set[str]]] = None
    ) -> List[Dict[str, Any]]:
        cluster_metrics = []
        
        for cluster in clusters:
            urls = cluster.get("urls", [])
            cluster_id = cluster.get("cluster_id")
            
            if len(urls) < 2:
                cluster_metrics.append({
                    "cluster_id": cluster_id,
                    "size": len(urls),
                    "internal_links": 0,
                    "external_links": 0,
                    "coherence_score": 0.0
                })
                continue
            
            internal_links = 0
            external_links = 0
            
            if graph:
                url_set = set(urls)
                
                for url in urls:
                    if url in graph:
                        for target in graph[url]:
                            if target in url_set:
                                internal_links += 1
                            else:
                                external_links += 1
            
            total_possible = len(urls) * (len(urls) - 1)
            coherence_score = internal_links / total_possible if total_possible > 0 else 0.0
            
            cluster_metrics.append({
                "cluster_id": cluster_id,
                "size": len(urls),
                "internal_links": internal_links,
                "external_links": external_links,
                "coherence_score": coherence_score
            })
        
        return cluster_metrics
    
    def full_proximity_analysis(
        self,
        project_id: str,
        vectors: np.ndarray,
        node_ids: List[str],
        urls: List[str],
        semantic_neighbors: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
        edges_data: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        graph = self.build_link_graph(project_id, edges_data)
        
        proximity_anomalies = self.find_proximity_anomalies(
            vectors, node_ids, urls, semantic_neighbors, graph
        )
        
        cluster_coherence = self.calculate_cluster_coherence(clusters, graph)
        
        analysis_summary = {
            "total_pages": len(node_ids),
            "semantic_pairs": len(semantic_neighbors),
            "proximity_anomalies": len(proximity_anomalies),
            "avg_anomaly_score": np.mean([p["anomaly_score"] for p in proximity_anomalies]) if proximity_anomalies else 0.0,
            "clusters_with_links": len([c for c in cluster_coherence if c["internal_links"] > 0]),
            "avg_cluster_coherence": np.mean([c["coherence_score"] for c in cluster_coherence])
        }
        
        return {
            "proximity_anomalies": proximity_anomalies,
            "cluster_coherence": cluster_coherence,
            "summary": analysis_summary,
            "graph_stats": {
                "total_nodes": len(graph) if graph else 0,
                "total_edges": sum(len(targets) for targets in graph.values()) if graph else 0
            }
        }