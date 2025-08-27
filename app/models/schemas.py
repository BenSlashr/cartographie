from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from uuid import UUID

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    created_at: str
    status: str

class ImportResult(BaseModel):
    project_id: str
    rows: int
    path: str
    message: str

class EmbeddingItem(BaseModel):
    type: str  # "text" or "url"
    value: str

class EmbeddingBatch(BaseModel):
    items: List[EmbeddingItem]

class EmbeddingResponse(BaseModel):
    vectors: List[List[float]]
    dims: int
    normalized: bool

class ClusterInfo(BaseModel):
    cluster_id: int
    size: int
    centroid: List[float]
    urls: List[str]
    theme: Optional[str] = None

class ProximityItem(BaseModel):
    node_i: str
    node_j: str
    url_i: HttpUrl
    url_j: HttpUrl
    cosine: float
    hops: Optional[int]
    anomaly_score: float

class AnalysisResult(BaseModel):
    project_id: str
    total_pages: int
    clusters: List[ClusterInfo]
    proximities: List[ProximityItem]
    projection_2d: List[Dict[str, Any]]

class ExportRequest(BaseModel):
    format: str  # "csv", "json", "parquet"
    include_vectors: bool = False