from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.models.job_schemas import JobResponse, JobStatusResponse, JobStatus
from app.tasks.embeddings_tasks import generate_embeddings_task, full_analysis_task

router = APIRouter()

@router.post("/{project_id}/embed-async", response_model=JobResponse)
async def start_embeddings_job(project_id: str):
    """Démarrer la génération d'embeddings en mode asynchrone"""
    try:
        job = generate_embeddings_task.delay(project_id)
        return JobResponse(
            job_id=job.id,
            status=JobStatus.PENDING,
            message="Génération d'embeddings démarrée"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du démarrage du job: {str(e)}")

@router.post("/{project_id}/analyze-async", response_model=JobResponse)
async def start_full_analysis_job(project_id: str):
    """Démarrer l'analyse complète en mode asynchrone"""
    try:
        print(f"🎪 JOB_ENDPOINT: Starting analysis for project {project_id}")
        print(f"🎪 JOB_ENDPOINT: full_analysis_task = {full_analysis_task}")
        print(f"🎪 JOB_ENDPOINT: About to call full_analysis_task.delay()")
        
        job = full_analysis_task.delay(project_id)
        
        print(f"🎪 JOB_ENDPOINT: Job created with ID: {job.id}")
        print(f"🎪 JOB_ENDPOINT: Job state: {job.state}")
        print(f"🎪 JOB_ENDPOINT: Job ready: {job.ready()}")
        
        return JobResponse(
            job_id=job.id,
            status=JobStatus.PENDING,
            message="Analyse complète démarrée"
        )
    except Exception as e:
        print(f"🎪 JOB_ENDPOINT ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🎪 JOB_ENDPOINT TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du démarrage du job: {str(e)}")

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Récupérer le statut d'un job avec progress détaillé"""
    try:
        job = AsyncResult(job_id, app=celery_app)
        state = job.state or 'PENDING'
        
        # Retourner les infos de progression détaillées
        progress_info = {"status": f"État: {state}"}
        if state == 'PROGRESS' and job.info:
            progress_info = job.info
        
        return {
            "job_id": job_id,
            "status": state,
            "progress": progress_info,
            "result": None if state != 'SUCCESS' else job.result
        }
        
    except Exception as e:
        return {
            "job_id": job_id,
            "status": "ERROR", 
            "error": f"Erreur: {str(e)}",
            "progress": {"status": "Erreur de récupération"}
        }

@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Annuler un job"""
    try:
        celery_app.control.revoke(job_id, terminate=True)
        return {"message": f"Job {job_id} annulé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'annulation: {str(e)}")

@router.get("/")
async def list_active_jobs():
    """Lister les jobs actifs"""
    try:
        inspect = celery_app.control.inspect()
        active_jobs = inspect.active()
        
        if active_jobs:
            all_jobs = []
            for worker, jobs in active_jobs.items():
                for job in jobs:
                    all_jobs.append({
                        "job_id": job["id"],
                        "worker": worker,
                        "name": job["name"],
                        "args": job["args"]
                    })
            return {"active_jobs": all_jobs}
        else:
            return {"active_jobs": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des jobs: {str(e)}")