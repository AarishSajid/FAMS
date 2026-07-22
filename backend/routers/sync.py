from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from services.sync_service import run_sync
from dependencies import authorize
from enums import UserRole

router = APIRouter(prefix="/sync", tags=["Sync"])

class SyncResponse(BaseModel):
    message: str

@router.post("/trigger", response_model=SyncResponse)
def trigger_sync(
    background_tasks: BackgroundTasks,
    _user=Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.ADMIN))
):
    """Manually triggers the Agriverse sync service to run immediately in the background."""
    background_tasks.add_task(run_sync)
    return {"message": "Sync started in background."}
