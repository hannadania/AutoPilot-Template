from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import datetime

# Correct import for your template's db session
from app.core.database import get_db

router = APIRouter(prefix="/api/policies", tags=["Policies"])

# Matches Hanna's custom Pydantic schema
class PolicyUpdate(BaseModel):
    is_active: bool
    value: Optional[Dict[str, Any]] = None


# Evaluation Request payload sent by your Supervity Orchestrator
class PolicyEvaluationRequest(BaseModel):
    item_number: str
    proposed_cost: float
    customer_priority: str  # 'critical', 'high', 'medium', 'low'
    triggers_penalty: bool


@router.on_event("startup")
def init_policies_table():
    """
    Self-healing database table setup. Ensures the ai_policies table
    exists on startup and seeds Hanna's custom rules if empty.
    """
    db = next(get_db())
    try:
        # 1. Create table with structured JSON capability
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_policies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                natural_language TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                value_json JSONB,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        db.commit()

        # 2. Seed Hanna's 3 mandatory default policies if table is brand new
        count = db.execute(text("SELECT COUNT(*) FROM ai_policies")).scalar()
        if count == 0:
            db.execute(text("""
                INSERT INTO ai_policies (id, name, description, natural_language, is_active, value_json)
                VALUES 
                (
                    'expedite-spend-limit', 
                    'Expedite Spend Limit', 
                    'Requires executive sign-off for freight expedites exceeding a specific limit.', 
                    'If expedite cost exceeds the threshold, trigger executive approval workflow.', 
                    true, 
                    '{"limit": 50000.0}'::jsonb
                ),
                (
                    'min-customer-priority', 
                    'Minimum Customer Priority Tier', 
                    'Determines the lowest priority tier allowed to trigger auto-approvals.', 
                    'Allow auto-reallocation only for customers ranked at or above this tier.', 
                    true, 
                    '{"tier": "high"}'::jsonb
                ),
                (
                    'allow-penalty-clauses', 
                    'Allow Contract Penalty Expedites', 
                    'Blocks automatic expedites if they trigger contract penalty surcharges or void rebates.', 
                    'If an expedite triggers contract penalties, escalate to human commander.', 
                    true, 
                    '{"allow": false}'::jsonb
                );
            """))
            db.commit()
            print("🌱 Hanna's AI Policies seeded successfully!")
    except Exception as e:
        print(f"⚠️ Seed/Init warning: {str(e)}")


@router.get("")
async def get_all_policies(db: Session = Depends(get_db)):
    """
    Called by Next.js to display your live AI Policies dashboard page.
    """
    query = text("SELECT * FROM ai_policies ORDER BY id ASC")
    rows = db.execute(query).mappings().all()
    
    # Map SQL rows back into the clean dict format Next.js expects
    policies_list = []
    for row in rows:
        policies_list.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "natural_language": row["natural_language"],
            "is_active": row["is_active"],
            "value": row["value_json"]
        })
    return {"policies": policies_list}


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str, 
    payload: PolicyUpdate, 
    db: Session = Depends(get_db)
):
    """
    Triggers when a business user slides or toggles a rule on the frontend UI.
    Saves the new settings directly into Supabase.
    """
    # Verify the rule exists
    check = db.execute(
        text("SELECT id FROM ai_policies WHERE id = :id"), 
        {"id": policy_id}
    ).first()
    
    if not check:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Update database row
    update_query = text("""
        UPDATE ai_policies 
        SET is_active = :active, value_json = :val, updated_at = NOW()
        WHERE id = :id
    """)
    
    import json
    db.execute(update_query, {
        "active": payload.is_active,
        "val": json.dumps(payload.value) if payload.value else None,
        "id": policy_id
    })
    db.commit()
    
    print(f"⚖️ POLICY RULE EDITED: '{policy_id}' updated to active={payload.is_active}, value={payload.value}")
    return {"status": "success", "message": f"Policy '{policy_id}' successfully updated."}


@router.post("/evaluate")
async def evaluate_policies(
    request: PolicyEvaluationRequest, 
    db: Session = Depends(get_db)
):
    """
    Called by your Supervity Orchestrator to decide if the AI can act 
    autonomously or must escalate to the custom human Workbench.
    """
    # 1. Fetch current policy settings from database
    rows = db.execute(text("SELECT id, is_active, value_json FROM ai_policies")).mappings().all()
    rules = {row["id"]: row for row in rows}

    decision = "APPROVE"
    escalation_reasons = []
    priority_ranking = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    # --- Rule 1: Spend Limit ---
    spend_rule = rules.get("expedite-spend-limit")
    if spend_rule and spend_rule["is_active"]:
        val = spend_rule["value_json"] or {}
        limit = float(val.get("limit", 50000.0))
        if request.proposed_cost > limit:
            decision = "ESCALATE"
            escalation_reasons.append(f"Proposed cost (RM {request.proposed_cost:,.2f}) exceeds spend threshold (RM {limit:,.2f})")

    # --- Rule 2: Customer Priority ---
    priority_rule = rules.get("min-customer-priority")
    if priority_rule and priority_rule["is_active"]:
        val = priority_rule["value_json"] or {}
        min_tier = val.get("tier", "high").lower()
        
        req_rank = priority_ranking.get(request.customer_priority.lower(), 0)
        min_rank = priority_ranking.get(min_tier, 3)

        if req_rank < min_rank:
            decision = "ESCALATE"
            escalation_reasons.append(f"Customer priority '{request.customer_priority}' is below minimum required tier '{min_tier}'")

    # --- Rule 3: Contract Penalties Surcharge ---
    penalty_rule = rules.get("allow-penalty-clauses")
    if penalty_rule and penalty_rule["is_active"]:
        val = penalty_rule["value_json"] or {}
        is_allowed = val.get("allow", False)
        if request.triggers_penalty and not is_allowed:
            decision = "ESCALATE"
            escalation_reasons.append("Action triggers an active contract penalty clause which is currently banned by policy")

    # ⚖️ AUDIT TRAIL LOGGING (Required for compliance points!)
    log_msg = f"📋 EVALUATION FOR {request.item_number}: DECISION = {decision}"
    if escalation_reasons:
        log_msg += f" | ESCALATED DUE TO: {', '.join(escalation_reasons)}"
    print(log_msg)

    return {
        "decision": decision,
        "escalation_reasons": escalation_reasons,
        "timestamp": datetime.datetime.now().isoformat()
    }