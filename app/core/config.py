from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    EMBEDDINGS_ENDPOINT: str = "https://outils.agence-slashr.fr/embedding"
    EMBED_BATCH: int = 250
    KNN_K: int = 20
    DMAX: int = 8
    SIM_THRESHOLD: float = 0.80
    HOPS_THRESHOLD: int = 3
    CHUNKING: bool = False
    DATA_DIR: str = "./data"
    
    class Config:
        env_file = ".env"

settings = Settings()