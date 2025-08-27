from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class JobProgress(BaseModel):
    current: int
    total: int
    status: str
    pages_processed: Optional[int] = None
    total_pages: Optional[int] = None
    step: Optional[int] = None
    total_steps: Optional[int] = None