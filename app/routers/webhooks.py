import httpx
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(tags=["Webhooks"])

# This must match your .env variable
SUPERVITY_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lcklkIjoiY21yZzlpZ3Z2MDFmYmxuNWozOGRhMTFmbyIsInN1YiI6Ijg1N2I3ZmQ0LTJhNTgtNDUyOS04MWE4LTIxNzRhZDI2NmQ0ZCIsImdyb3VwcyI6WyIvQXZvY2Fkb3MgYXQgSVQvQXZvY2Fkb3MgYXQgSVQvUm9sZXMvQWRtaW5zIiwiL0F2b2NhZG9zIGF0IElUL1JvbGVzL0FkbWlucyIsIi9Bdm9jYWRvcyBhdCBJVCJdLCJpYXQiOjE3ODYxMzIyODcsImV4cCI6NDkzOTczMjI4N30.oRFf1T3HK0bMA4wkuMB9DDZu9EsGtECWshLfE4vapGE"

class SupervityApprovalPayload(BaseModel):
    run_id: str
    operator_name: str
    item_number: str
    proposed_action: str
    cost_impact: str
    jira_ticket_url: str

@router.post("/supervity/workbench")
async def catch_ai_approval(payload: SupervityApprovalPayload, db: Session = Depends(get_db)):
    """
    Catches data from Supervity and cues it in your database.
    Final Path: POST /api/webhooks/supervity/workbench
    """
    # Self-heal the database table if it doesn't exist
    setup_query = text("""
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id SERIAL PRIMARY KEY,
            run_id TEXT NOT NULL,
            operator_name TEXT NOT NULL,
            item_number TEXT NOT NULL,
            proposed_action TEXT NOT NULL,
            cost_impact TEXT NOT NULL,
            jira_ticket_url TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    db.execute(setup_query)
    
    insert_query = text("""
        INSERT INTO pending_tasks (run_id, operator_name, item_number, proposed_action, cost_impact, jira_ticket_url, status)
        VALUES (:run_id, :op, :item, :action, :cost, :jira, 'PENDING')
    """)
    db.execute(insert_query, {
        "run_id": payload.run_id, "op": payload.operator_name, "item": payload.item_number,
        "action": payload.proposed_action, "cost": payload.cost_impact, "jira": payload.jira_ticket_url
    })
    db.commit()
    return {"status": "success", "message": "Disruption routed to Workbench"}

@router.put("/supervity/workbench/{item_number}/approve")
async def approve_task(item_number: str, db: Session = Depends(get_db)):
    # 1. Get the LATEST pending run
    get_query = text("""
        SELECT run_id FROM pending_tasks 
        WHERE item_number = :item AND status = 'PENDING' 
        ORDER BY created_at DESC LIMIT 1
    """)
    task = db.execute(get_query, {"item": item_number}).mappings().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="No pending task found for this SKU")
    
    run_id = task["run_id"]
    
    # 🟢 FIXED URL: Added 'workflow-' before 'runs'
    resume_url = f"https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/{run_id}/resume"
    
    print(f"DEBUG: Attempting to resume Run ID: {run_id}")
    print(f"DEBUG: Calling URL: {resume_url}")

    headers = {
        "Authorization": f"Bearer {SUPERVITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"status": "approved", "notes": "Approved via custom Command Center"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(resume_url, json=payload, headers=headers, timeout=15.0)
            print(f"DEBUG: Supervity Cloud Responded -> {response.status_code} {response.text}")
            
            if response.is_error:
                raise HTTPException(status_code=response.status_code, detail=f"Supervity Error: {response.text}")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Connection failed")

    # 4. Success - Update local DB
    db.execute(text("UPDATE pending_tasks SET status = 'APPROVED' WHERE run_id = :rid"), {"rid": run_id})
    db.commit()
    return {"status": "success", "message": f"Run {run_id} resumed"}