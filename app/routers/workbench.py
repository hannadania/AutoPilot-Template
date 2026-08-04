from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import datetime

# 🚨 CORRECTED IMPORT PATH 🚨
from app.core.database import get_db

router = APIRouter(tags=["Workbench"])

# This defines the data Supervity will send to your dashboard
class SupervityApprovalPayload(BaseModel):
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
    and routes them to PostgreSQL.
    """
    print(f"🚨 EXCEPTION CAUGHT: {payload.item_number} from {payload.operator_name}")
    
    # 1. HACKATHON TRICK: Force create the table in whatever DB we are connected to!
    setup_query = text("""
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id SERIAL PRIMARY KEY,
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
    
    # 2. Now insert the data safely!
    insert_query = text("""
        INSERT INTO pending_tasks (operator_name, item_number, proposed_action, cost_impact, jira_ticket_url, status)
        VALUES (:op, :item, :action, :cost, :jira, 'PENDING')
    """)
    
    db.execute(insert_query, {
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







@router.get("/api/webhooks/supervity/workbench")
async def get_pending_approvals(db: Session = Depends(get_db)):
    """
    Next.js UI calls this to fetch the queue of pending exceptions.
    """
    select_query = text("SELECT * FROM pending_tasks WHERE status = 'PENDING' ORDER BY created_at DESC")
    result = db.execute(select_query).mappings().all()
    
    # Convert SQLAlchemy results to a list of standard Python dictionaries
    return {"tasks": [dict(row) for row in result]}

@router.put("/api/webhooks/supervity/workbench/{item_number}/approve")
async def approve_task(item_number: str, db: Session = Depends(get_db)):
    """
    Next.js UI calls this when the human clicks 'Approve Action'.
    """
    update_query = text("""
        UPDATE pending_tasks 
        SET status = 'APPROVED' 
        WHERE item_number = :item
    """)
    
    db.execute(update_query, {"item": item_number})
    db.commit()
    
    return {"status": "success", "message": f"Task {item_number} approved."}