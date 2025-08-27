import asyncio
from celery import current_task
from app.core.celery_app import celery_app
from app.services.embeddings import EmbeddingsService
from app.services.index import VectorIndexService
from app.services.clustering import ClusteringService
from app.services.scoring import ScoringService

@celery_app.task(bind=True)
def generate_embeddings_task(self, project_id: str):
    """Tâche asynchrone pour générer les embeddings"""
    try:
        embeddings_service = EmbeddingsService()
        
        # Mettre à jour le statut
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 0, 'status': 'Chargement des pages...'}
        )
        
        # Lancer la génération d'embeddings de façon synchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                embeddings_service.embed_pages_with_progress(project_id, self.update_state)
            )
        finally:
            loop.close()
        
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': f'Embeddings générés pour {result["total_embeddings"]} pages'
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'status': f'Erreur: {str(e)}'}
        )
        raise

@celery_app.task(bind=True)
def full_analysis_task(self, project_id: str):
    """Tâche asynchrone pour l'analyse complète (embeddings + clustering + scoring)"""
    print(f"DEBUG: Starting full_analysis_task for project {project_id}")
    try:
        # Services
        embeddings_service = EmbeddingsService()
        index_service = VectorIndexService()
        clustering_service = ClusteringService()
        scoring_service = ScoringService()
        print(f"DEBUG: Services initialized")
        
        # Étape 1: Embeddings
        print(f"DEBUG: Starting embeddings step for project {project_id}")
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 4, 'status': 'Génération des embeddings...', 'step': 1, 'total_steps': 4}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"DEBUG: About to call embed_pages_with_progress")
            
            def progress_callback(state, meta):
                print(f"🎯 PROGRESS_CALLBACK: Called with state={state}")
                print(f"🎯 PROGRESS_CALLBACK: Original meta = {meta}")
                
                # Enrichir les métadonnées avec des détails sur les embeddings
                enriched_meta = {
                    **meta,
                    'step': 1,
                    'total_steps': 4,
                    'step_name': 'Génération des embeddings'
                }
                
                # Si on a des infos de batch, les inclure
                if 'pages_processed' in meta and 'total_pages' in meta:
                    progress_pct = (meta['pages_processed'] / meta['total_pages']) * 100
                    enriched_meta['progress_percentage'] = round(progress_pct, 1)
                    print(f"🎯 PROGRESS_CALLBACK: Calculated progress = {progress_pct}%")
                
                print(f"🎯 PROGRESS_CALLBACK: Enriched meta = {enriched_meta}")
                print(f"🎯 PROGRESS_CALLBACK: About to call self.update_state()")
                
                self.update_state(state=state, meta=enriched_meta)
                print(f"🎯 PROGRESS_CALLBACK: self.update_state() completed")
            
            embeddings_result = loop.run_until_complete(
                embeddings_service.embed_pages_with_progress(project_id, progress_callback)
            )
            print(f"DEBUG: embed_pages_with_progress completed, got {len(embeddings_result.get('vectors_array', []))} vectors")
        finally:
            loop.close()
        
        vectors = embeddings_result["vectors_array"]
        node_ids = embeddings_result["node_ids"]
        urls = embeddings_result["urls"]
        
        # Étape 2: Index vectoriel et voisins sémantiques
        self.update_state(
            state='PROGRESS',
            meta={'current': 2, 'total': 4, 'status': 'Calcul des similarités sémantiques...'}
        )
        
        semantic_neighbors = index_service.find_semantic_neighbors(vectors, node_ids)
        
        # Étape 3: Clustering
        self.update_state(
            state='PROGRESS',
            meta={'current': 3, 'total': 4, 'status': 'Analyse des clusters...'}
        )
        
        clustering_results = clustering_service.full_clustering_analysis(vectors, node_ids, urls)
        
        # Étape 4: Scoring proximité
        self.update_state(
            state='PROGRESS',
            meta={'current': 4, 'total': 4, 'status': 'Calcul des anomalies de proximité...'}
        )
        
        proximity_analysis = scoring_service.full_proximity_analysis(
            project_id, vectors, node_ids, urls, semantic_neighbors, clustering_results["clusters"]
        )
        
        # Résultat final
        final_result = {
            "project_id": project_id,
            "total_pages": len(node_ids),
            "clusters": clustering_results["clusters"],
            "proximities": proximity_analysis["proximity_anomalies"],
            "projection_2d": clustering_results["projection_2d"],
            "summary": proximity_analysis.get("summary", {})
        }
        
        return {
            'status': 'SUCCESS',
            'result': final_result,
            'message': f'Analyse complète terminée: {len(node_ids)} pages, {len(clustering_results["clusters"])} clusters, {len(proximity_analysis["proximity_anomalies"])} anomalies détectées'
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'status': f'Erreur: {str(e)}'}
        )
        raise