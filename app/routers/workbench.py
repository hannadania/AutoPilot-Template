from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
import os

# Corrected database import path from your template
from app.core.database import get_db

router = APIRouter(tags=["Workbench"])

# We fetch your Supervity API Key from your local environment file
SUPERVITY_API_KEY = os.getenv("SUPERVITY_API_KEY", "YOUR_SUPERVITY_API_KEY")

# This matches the dynamic payload Supervity will send to your laptop
class SupervityApprovalPayload(BaseModel):
    run_id: str              # Unique system ID of the paused run
    operator_name: str
    item_number: str
    proposed_action: str
    cost_impact: str
    jira_ticket_url: str


@router.post("/api/webhooks/supervity/workbench")
async def catch_ai_approval(
    payload: SupervityApprovalPayload,
    db: Session = Depends(get_db)
):
    """
    Catches human-in-the-loop approval requests from Supervity Auto
    and inserts them into your local PostgreSQL database.
    """
    print(f"🚨 EXCEPTION CAUGHT: {payload.item_number} from {payload.operator_name} (Run: {payload.run_id})")
    
    # Hanna's Dynamic Table Trick: Self-heal the database table if it doesn't exist
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
    db.commit()
    
    # Insert the paused run details including the run_id
    insert_query = text("""
        INSERT INTO pending_tasks (run_id, operator_name, item_number, proposed_action, cost_impact, jira_ticket_url, status)
        VALUES (:run_id, :op, :item, :action, :cost, :jira, 'PENDING')
    """)
    
    db.execute(insert_query, {
        "run_id": payload.run_id,
        "op": payload.operator_name,
        "item": payload.item_number,
        "action": payload.proposed_action,
        "cost": payload.cost_impact,
        "jira": payload.jira_ticket_url
    })
    db.commit()
    
    return {
        "status": "success", 
        "message": "Approval successfully routed to the Command Center Workbench"
    }


@router.get("/api/workbench/tasks")
async def get_pending_approvals(db: Session = Depends(get_db)):
    """
    Called by your Next.js UI to display the active queue of exceptions.
    """
    select_query = text("SELECT * FROM pending_tasks WHERE status = 'PENDING' ORDER BY created_at DESC")
    result = db.execute(select_query).mappings().all()
    
    return {"tasks": [dict(row) for row in result]}



@router.put("/api/webhooks/supervity/workbench/{item_number}/approve")
async def approve_task(item_number: str, db: Session = Depends(get_db)):
    # 1. Pull the specific task and its dynamic run_id from the database
    select_query = text("SELECT run_id FROM pending_tasks WHERE item_number = :item AND status = 'PENDING'")
    task = db.execute(select_query, {"item": item_number}).mappings().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Pending task not found for this item.")

    # 2. Construct the resume URL using the ACTUAL UUID stored in your DB
    # This fixes the 404 error by replacing human-readable names with system IDs
    resume_url = f"https://api.supervity.ai/v1/runs/{task['run_id']}/resume"
    
    # 3. Call the Supervity API to wake up the paused AI Agent
    async with httpx.AsyncClient() as client:
        response = await client.post(
            resume_url,
            headers={"Authorization": f"Bearer {SUPERVITY_API_KEY}"},
            json={"decision": "Approved", "notes": "Authorized via Command Center Workbench"}
        )
        
    if response.status_code != 200:
        print(f"❌ Supervity API Error: {response.status_code} - {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Failed to resume cloud agent.")

    # 4. Update your local database status to reflect the approval
    update_query = text("UPDATE pending_tasks SET status = 'APPROVED' WHERE item_number = :item")
    db.execute(update_query, {"item": item_number})
    db.commit()

    return {
        "status": "success", 
        "message": f"Cloud agent for {item_number} has been remotely resumed."
    }
