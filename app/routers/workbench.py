from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/api/workbench", tags=["Workbench"])
webhooks_router = APIRouter(tags=["Webhooks"])

@router.get("/tasks")
async def get_pending_approvals(db: Session = Depends(get_db)):
    """
    Called by your Next.js UI to display the active queue of exceptions.
    Final Path: GET /api/workbench/tasks
    """
    # Note: We use raw SQL here to match the 'self-healing' table created in webhooks
    select_query = text("SELECT * FROM pending_tasks WHERE status = 'PENDING' ORDER BY created_at DESC")
    result = db.execute(select_query).mappings().all()
    
    return {"tasks": [dict(row) for row in result]}
