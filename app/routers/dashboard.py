from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    # 1. Active Disruptions: Count of PENDING tasks
    active_query = text("SELECT count(*) FROM pending_tasks WHERE status = 'PENDING'")
    active_count = db.execute(active_query).scalar() or 0

    # 2. Success Rate: APPROVED vs REJECTED
    approved_query = text("SELECT count(*) FROM pending_tasks WHERE status = 'APPROVED'")
    rejected_query = text("SELECT count(*) FROM pending_tasks WHERE status = 'REJECTED'")
    
    approved_count = db.execute(approved_query).scalar() or 0
    rejected_count = db.execute(rejected_query).scalar() or 0
    
    total_resolved = approved_count + rejected_count
    success_rate = (approved_count / total_resolved * 100) if total_resolved > 0 else 100

    # 3. Cost Avoided: Summing impact values
    # Note: Using SQL casting to handle the TEXT format of cost_impact
    cost_query = text("""
        SELECT SUM(CAST(NULLIF(regexp_replace(cost_impact, '[^0-9.]', '', 'g'), '') AS NUMERIC)) 
        FROM pending_tasks
    """)
    total_cost = db.execute(cost_query).scalar() or 0

    return {
        "active_disruptions": active_count,
        "success_rate": f"{round(success_rate, 1)}%",
        "cost_avoided": f"MYR {total_cost:,.2f}",
        "total_tasks": active_count + total_resolved
    }