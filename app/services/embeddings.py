import httpx
import asyncio
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from app.core.config import settings
from app.models.schemas import EmbeddingItem, EmbeddingBatch

class EmbeddingsService:
    def __init__(self):
        self.endpoint = settings.EMBEDDINGS_ENDPOINT
        self.batch_size = settings.EMBED_BATCH
        self.data_dir = Path(settings.DATA_DIR)
        print(f"🏗️ EMBEDDINGS_SERVICE: Initialized with FORCED batch_size = {self.batch_size}")
    
    async def embed_batch(self, items: List[EmbeddingItem]) -> List[List[float]]:
        print(f"🚀 EMBED_BATCH: Starting with {len(items)} items using REAL API")
        
        # Préparer les données pour l'API v1/embeddings (format OpenAI-compatible)
        api_items = []
        for item in items:
            api_items.append({
                "type": "text",
                "value": item.value  # Le contenu est déjà extrait et nettoyé
            })
        
        payload = {
            "model": "BAAI/bge-m3",
            "input": api_items
        }
        
        full_url = f"{self.endpoint}/v1/embeddings"
        print(f"🔄 EMBED_BATCH: Calling API with {len(api_items)} items")
        print(f"🌐 EMBED_BATCH: Full URL: {full_url}")
        print(f"📝 EMBED_BATCH: Payload: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=3600.0) as client:  # 1h timeout
                response = await client.post(
                    full_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"🔍 EMBED_BATCH: API Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    # Format OpenAI : result["data"][i]["embedding"]
                    vectors = [item["embedding"] for item in result.get("data", [])]
                    print(f"✅ EMBED_BATCH: Successfully got {len(vectors)} vectors from API")
                    return vectors
                else:
                    error_text = response.text
                    print(f"❌ EMBED_BATCH: API Error {response.status_code}: {error_text}")
                    raise Exception(f"API Error {response.status_code}: {error_text}")
                    
        except httpx.TimeoutException as e:
            print(f"⏰ EMBED_BATCH: Timeout error: {str(e)}")
            raise Exception(f"Timeout calling embeddings API: {str(e)}")
        except Exception as e:
            print(f"💥 EMBED_BATCH: Unexpected error: {type(e).__name__}: {str(e)}")
            raise Exception(f"Error calling embeddings API: {str(e)}")
    
    async def embed_pages_with_progress(self, project_id: str, update_callback=None) -> Dict[str, Any]:
        """Version avec callback de progression"""
        print(f"🚀 EMBED_PAGES: Starting for project {project_id}")
        project_dir = self.data_dir / project_id
        pages_path = project_dir / "pages.csv"
        print(f"🚀 EMBED_PAGES: Looking for pages file at: {pages_path}")
        
        if not pages_path.exists():
            print(f"🚀 EMBED_PAGES ERROR: File not found: {pages_path}")
            raise FileNotFoundError(f"Fichier pages.csv non trouvé pour le projet {project_id}")
        
        print(f"🚀 EMBED_PAGES: Pages file found, proceeding with embeddings")
        
        df = pd.read_csv(pages_path)
        print(f"🚀 EMBED_PAGES: Loaded {len(df)} rows from CSV")
        
        items = []
        for idx, row in df.iterrows():
            if row["contenu"] and str(row["contenu"]).strip():
                item = EmbeddingItem(type="text", value=str(row["contenu"]))
                print(f"🚀 EMBED_PAGES: Row {idx} -> text item (content length: {len(str(row['contenu']))})")
            else:
                item = EmbeddingItem(type="url", value=str(row["url"]))
                print(f"🚀 EMBED_PAGES: Row {idx} -> url item: {row['url']}")
            items.append(item)
        
        print(f"🚀 EMBED_PAGES: Created {len(items)} embedding items")
        
        all_vectors = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        print(f"🚀 EMBED_PAGES: Will process {total_batches} batches of size {self.batch_size}")
        
        for i in range(0, len(items), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_items = items[i:i + self.batch_size]
            
            print(f"🔄 BATCH {batch_num}/{total_batches}: Starting with {len(batch_items)} pages (indices {i} to {i+len(batch_items)-1})")
            
            # Callback de progression AVANT
            if update_callback:
                print(f"🔄 BATCH {batch_num}: Calling progress callback BEFORE processing")
                callback_meta = {
                    'current': batch_num,
                    'total': total_batches,
                    'status': f'Traitement batch {batch_num}/{total_batches} ({len(batch_items)} pages)',
                    'pages_processed': i,
                    'total_pages': len(items)
                }
                print(f"🔄 BATCH {batch_num}: Callback meta = {callback_meta}")
                update_callback(state='PROGRESS', meta=callback_meta)
                print(f"🔄 BATCH {batch_num}: Progress callback BEFORE completed")
            else:
                print(f"🔄 BATCH {batch_num}: No update_callback provided")
            
            try:
                print(f"🔄 BATCH {batch_num}: About to call embed_batch()")
                batch_vectors = await self.embed_batch(batch_items)
                all_vectors.extend(batch_vectors)
                print(f"✅ BATCH {batch_num}/{total_batches}: COMPLETED - got {len(batch_vectors)} vectors, total so far: {len(all_vectors)}")
                
                # Update de progression APRÈS completion du batch
                if update_callback:
                    pages_completed = i + len(batch_items)
                    print(f"✅ BATCH {batch_num}: Calling progress callback AFTER processing - {pages_completed}/{len(items)} pages completed")
                    callback_meta_after = {
                        'current': batch_num,
                        'total': total_batches,
                        'status': f'Batch {batch_num}/{total_batches} terminé ({pages_completed}/{len(items)} pages)',
                        'pages_processed': pages_completed,
                        'total_pages': len(items)
                    }
                    print(f"✅ BATCH {batch_num}: Callback meta AFTER = {callback_meta_after}")
                    update_callback(state='PROGRESS', meta=callback_meta_after)
                    print(f"✅ BATCH {batch_num}: Progress callback AFTER completed")
                    
            except Exception as e:
                print(f"❌ BATCH {batch_num} FAILED: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"❌ BATCH {batch_num} TRACEBACK: {traceback.format_exc()}")
                raise
            
            # Petite pause entre les batches
            await asyncio.sleep(0.1)
        
        # Sauvegarder les résultats
        embeddings_df = pd.DataFrame({
            "node_id": df["node_id"],
            "url": df["url"],
            "vector": all_vectors
        })
        
        embeddings_path = project_dir / "embeddings.parquet"
        embeddings_df.to_parquet(embeddings_path)
        
        vectors_array = np.array(all_vectors, dtype=np.float32)
        
        # Détecter automatiquement le nombre de dimensions
        dimensions = len(all_vectors[0]) if all_vectors else 384
        
        return {
            "project_id": project_id,
            "total_embeddings": len(all_vectors),
            "dimensions": dimensions,
            "embeddings_path": str(embeddings_path),
            "vectors_array": vectors_array,
            "node_ids": df["node_id"].tolist(),
            "urls": df["url"].tolist()
        }

    async def embed_pages(self, project_id: str) -> Dict[str, Any]:
        project_dir = self.data_dir / project_id
        pages_path = project_dir / "pages.csv"
        
        if not pages_path.exists():
            raise FileNotFoundError(f"Fichier pages.csv non trouvé pour le projet {project_id}")
        
        df = pd.read_csv(pages_path)
        
        items = []
        for _, row in df.iterrows():
            if row["contenu"] and str(row["contenu"]).strip():
                items.append(EmbeddingItem(type="text", value=str(row["contenu"])))
            else:
                items.append(EmbeddingItem(type="url", value=str(row["url"])))
        
        all_vectors = []
        
        for i in range(0, len(items), self.batch_size):
            batch_items = items[i:i + self.batch_size]
            batch_vectors = await self.embed_batch(batch_items)
            all_vectors.extend(batch_vectors)
            
            # Petite pause entre les batches pour éviter de surcharger le service
            await asyncio.sleep(0.1)
        
        embeddings_df = pd.DataFrame({
            "node_id": df["node_id"],
            "url": df["url"],
            "vector": all_vectors
        })
        
        embeddings_path = project_dir / "embeddings.parquet"
        embeddings_df.to_parquet(embeddings_path)
        
        vectors_array = np.array(all_vectors, dtype=np.float32)
        
        # Détecter automatiquement le nombre de dimensions
        dimensions = len(all_vectors[0]) if all_vectors else 384
        
        return {
            "project_id": project_id,
            "total_embeddings": len(all_vectors),
            "dimensions": dimensions,
            "embeddings_path": str(embeddings_path),
            "vectors_array": vectors_array,
            "node_ids": df["node_id"].tolist(),
            "urls": df["url"].tolist()
        }
    
    def load_embeddings(self, project_id: str) -> Dict[str, Any]:
        project_dir = self.data_dir / project_id
        embeddings_path = project_dir / "embeddings.parquet"
        
        if not embeddings_path.exists():
            raise FileNotFoundError(f"Fichier embeddings.parquet non trouvé pour le projet {project_id}")
        
        df = pd.read_parquet(embeddings_path)
        vectors_array = np.array(df["vector"].tolist(), dtype=np.float32)
        
        return {
            "vectors_array": vectors_array,
            "node_ids": df["node_id"].tolist(),
            "urls": df["url"].tolist()
        }