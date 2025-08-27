import faiss
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
from app.core.config import settings

class VectorIndexService:
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
        self.k = settings.KNN_K
    
    def build_index(self, vectors: np.ndarray) -> faiss.Index:
        if len(vectors.shape) != 2:
            raise ValueError(f"Forme attendue: (n, dimensions), reçue: {vectors.shape}")
        
        # Détecter automatiquement les dimensions
        dimensions = vectors.shape[1]
        
        vectors = vectors.astype(np.float32)
        
        norms = np.linalg.norm(vectors, axis=1)
        if not np.allclose(norms, 1.0, rtol=1e-5):
            vectors = vectors / norms[:, np.newaxis]
        
        index = faiss.IndexFlatIP(dimensions)
        index.add(vectors)
        
        return index
    
    def search_similar(
        self, 
        index: faiss.Index, 
        query_vectors: np.ndarray, 
        k: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        if k is None:
            k = self.k
        
        query_vectors = query_vectors.astype(np.float32)
        
        norms = np.linalg.norm(query_vectors, axis=1)
        if not np.allclose(norms, 1.0, rtol=1e-5):
            query_vectors = query_vectors / norms[:, np.newaxis]
        
        similarities, indices = index.search(query_vectors, k + 1)
        
        return similarities, indices
    
    def find_semantic_neighbors(
        self, 
        vectors: np.ndarray, 
        node_ids: List[str],
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        if similarity_threshold is None:
            similarity_threshold = settings.SIM_THRESHOLD
        
        index = self.build_index(vectors)
        similarities, indices = self.search_similar(index, vectors)
        
        neighbors = []
        
        for i, (sims, idxs) in enumerate(zip(similarities, indices)):
            for j, (sim, idx) in enumerate(zip(sims, idxs)):
                if j == 0:  # Skip self
                    continue
                
                if sim >= similarity_threshold:
                    neighbors.append({
                        "node_i": node_ids[i],
                        "node_j": node_ids[idx],
                        "similarity": float(sim),
                        "rank": j
                    })
        
        return neighbors
    
    def save_index(self, index: faiss.Index, project_id: str) -> str:
        project_dir = self.data_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        index_path = project_dir / "faiss_index.index"
        faiss.write_index(index, str(index_path))
        
        return str(index_path)
    
    def load_index(self, project_id: str) -> faiss.Index:
        project_dir = self.data_dir / project_id
        index_path = project_dir / "faiss_index.index"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index FAISS non trouvé pour le projet {project_id}")
        
        return faiss.read_index(str(index_path))