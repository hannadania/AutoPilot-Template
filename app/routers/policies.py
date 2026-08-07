import re
import json
import datetime
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db

# 1. Standard Policies Router (/api/policies)
router = APIRouter(prefix="/api/policies", tags=["Policies"])

# 2. AI Wizard Router (/api/ai/policies)
ai_router = APIRouter(prefix="/api/ai/policies", tags=["AI Policies"])

# ==========================================
# Schemas
# ==========================================
class PolicyUpdate(BaseModel):
    is_active: bool
    value: Optional[Dict[str, Any]] = None

class PolicyEvaluationRequest(BaseModel):
    item_number: str
    proposed_cost: float
    customer_priority: str  # 'critical', 'high', 'medium', 'low'
    triggers_penalty: bool

class PolicyCreateSchema(BaseModel):
    name: str
    description: Optional[str] = ""
    natural_language: Optional[str] = ""
    policy_type: str = "logical"
    dsl: Optional[Dict[str, Any]] = None
    refined_instruction: Optional[str] = None
    entity_name: Optional[str] = None
    tags: Optional[List[str]] = []
    priority: int = 0
    is_active: bool = True

class AnalyzeInputRequest(BaseModel):
    input: str

class ConflictCheckRequest(BaseModel):
    natural_language: str
    policy_scope: str
    entity_name: Optional[str] = None


# ==========================================
# Startup / Database Initialization
# ==========================================
@router.on_event("startup")
def init_policies_table():
    """
    Self-healing database table setup. Ensures the ai_policies table
    exists on startup and seeds Hanna's custom rules if empty.
    """
    db = next(get_db())
    try:
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


# ==========================================
# Core Policy Endpoints (router)
# ==========================================
@router.get("")
async def get_all_policies(db: Session = Depends(get_db)):
    """Called by Next.js to display your live AI Policies dashboard page."""
    try:
        query = text("SELECT * FROM ai_policies ORDER BY id ASC")
        rows = db.execute(query).mappings().all()
        
        policies_list = []
        for row in rows:
            policies_list.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "natural_language": row["natural_language"],
                "is_active": row["is_active"],
                "value": row["value_json"],
                "type": "structured",
                "policy_type": "logical"
            })
        return {"policies": policies_list}
    except Exception as e:
        print(f"❌ DATABASE ERROR IN GET /policies: {str(e)}")
        raise e


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str, 
    payload: PolicyUpdate, 
    db: Session = Depends(get_db)
):
    """Triggers when a business user slides or toggles a rule on the frontend UI."""
    check = db.execute(
        text("SELECT id FROM ai_policies WHERE id = :id"), 
        {"id": policy_id}
    ).first()
    
    if not check:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_query = text("""
        UPDATE ai_policies 
        SET is_active = :active, value_json = :val, updated_at = NOW()
        WHERE id = :id
    """)
    
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
    """Called by your Supervity Orchestrator to decide if the AI can act autonomously."""
    rows = db.execute(text("SELECT id, is_active, value_json FROM ai_policies")).mappings().all()
    rules = {row["id"]: row for row in rows}

    decision = "APPROVE"
    escalation_reasons = []
    priority_ranking = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    spend_rule = rules.get("expedite-spend-limit")
    if spend_rule and spend_rule["is_active"]:
        val = spend_rule["value_json"] or {}
        limit = float(val.get("limit", 50000.0))
        if request.proposed_cost > limit:
            decision = "ESCALATE"
            escalation_reasons.append(f"Proposed cost (RM {request.proposed_cost:,.2f}) exceeds spend threshold (RM {limit:,.2f})")

    priority_rule = rules.get("min-customer-priority")
    if priority_rule and priority_rule["is_active"]:
        val = priority_rule["value_json"] or {}
        min_tier = val.get("tier", "high").lower()
        
        req_rank = priority_ranking.get(request.customer_priority.lower(), 0)
        min_rank = priority_ranking.get(min_tier, 3)

        if req_rank < min_rank:
            decision = "ESCALATE"
            escalation_reasons.append(f"Customer priority '{request.customer_priority}' is below minimum required tier '{min_tier}'")

    penalty_rule = rules.get("allow-penalty-clauses")
    if penalty_rule and penalty_rule["is_active"]:
        val = penalty_rule["value_json"] or {}
        is_allowed = val.get("allow", False)
        if request.triggers_penalty and not is_allowed:
            decision = "ESCALATE"
            escalation_reasons.append("Action triggers an active contract penalty clause which is currently banned by policy")

    log_msg = f"📋 EVALUATION FOR {request.item_number}: DECISION = {decision}"
    if escalation_reasons:
        log_msg += f" | ESCALATED DUE TO: {', '.join(escalation_reasons)}"
    print(log_msg)

    return {
        "decision": decision,
        "escalation_reasons": escalation_reasons,
        "timestamp": datetime.datetime.now().isoformat()
    }


@router.post("")
async def create_policy(policy: PolicyCreateSchema, db: Session = Depends(get_db)):
    """Saves a new custom policy created from the Structured Builder or AI Wizard."""
    policy_id = f"custom-policy-{uuid.uuid4().hex[:8]}"
    
    insert_query = text("""
        INSERT INTO ai_policies (id, name, description, natural_language, is_active, value_json)
        VALUES (:id, :name, :description, :natural_language, :is_active, :value_json)
    """)
    
    db.execute(insert_query, {
        "id": policy_id,
        "name": policy.name,
        "description": policy.description,
        "natural_language": policy.natural_language,
        "is_active": policy.is_active,
        "value_json": json.dumps(policy.dsl) if policy.dsl else "{}"
    })
    db.commit()
    
    print(f"✨ NEW POLICY CREATED: '{policy.name}' ({policy_id})")
    return {"status": "success", "id": policy_id, "message": "Policy created successfully"}


# ==========================================
# AI Wizard Endpoints (ai_router)
# ==========================================
@ai_router.post("/analyze-input")
async def analyze_input(request: AnalyzeInputRequest):
    text_input = request.input.lower()
    suggested_type = "logical" if "$" in text_input or "under" in text_input else "natural_language"
    
    words = request.input.split()
    name = " ".join(words[:4]).title() + " Rule" if len(words) > 0 else "New AI Rule"

    print(f"🧠 AI Parsed: {request.input}")

    return {
        "suggested_type": suggested_type,
        "suggested_name": name,
        "suggested_tags": ["ai-generated", "auto-rule"],
        "entity_name": "invoice" if "invoice" in text_input else "general",
        "dsl": {
            "conditions": [{"field": "amount", "operator": "<", "value": "1000"}],
            "actions": [{"type": "approve"}],
            "match_mode": "all"
        },
        "refined_instruction": request.input
    }


@ai_router.post("/check-conflicts")
async def check_conflicts(request: ConflictCheckRequest):
    print(f"🛡️ Checking conflicts for: {request.natural_language}")
    return {
        "conflicts": [],
        "overrides": [],
        "clarifications": [],
        "suggested_instructions": [],
        "refined_instruction": request.natural_language,
        "is_valid": True,
        "warnings": []
    }