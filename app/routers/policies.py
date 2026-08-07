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

# 2. AI Policies Router (/api/ai/policies)
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
    customer_priority: str
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
    policy_scope: Optional[str] = "global"
    entity_name: Optional[str] = None


# ==========================================
# Core Policy Endpoints (router)
# ==========================================

@router.get("")
@router.get("/")
async def get_all_policies(db: Session = Depends(get_db)):
    """Called by Next.js to display your live AI Policies dashboard page."""
    print("🔍 DIAGNOSTIC HIT: GET /api/policies")
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
        print(f"✅ Found {len(policies_list)} policies in database.")
        return {"policies": policies_list}
    except Exception as e:
        print(f"❌ DATABASE ERROR IN GET /policies: {str(e)}")
        raise e


@router.post("")
@router.post("/")
async def create_policy(policy: PolicyCreateSchema, db: Session = Depends(get_db)):
    """Saves a new custom policy created from the Structured Builder or AI Wizard."""
    print(f"🚨 DIAGNOSTIC HIT: POST /api/policies - Saving '{policy.name}'")
    
    policy_id = f"custom-policy-{uuid.uuid4().hex[:8]}"
    
    try:
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
        print(f"✅ SUCCESSFULLY SAVED POLICY TO DB: {policy.name} ({policy_id})")
        return {"status": "success", "id": policy_id, "message": "Policy created successfully"}
    except Exception as e:
        print(f"❌ DATABASE ERROR ON SAVE: {str(e)}")
        db.rollback()
        raise e


@router.put("/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate, db: Session = Depends(get_db)):
    check = db.execute(text("SELECT id FROM ai_policies WHERE id = :id"), {"id": policy_id}).first()
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
    return {"status": "success", "message": f"Policy '{policy_id}' updated."}


@router.post("/evaluate")
async def evaluate_policies(request: PolicyEvaluationRequest, db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, is_active, value_json FROM ai_policies")).mappings().all()
    rules = {row["id"]: row for row in rows}

    decision = "APPROVE"
    escalation_reasons = []

    spend_rule = rules.get("expedite-spend-limit")
    if spend_rule and spend_rule["is_active"]:
        val = spend_rule["value_json"] or {}
        limit = float(val.get("limit", 50000.0))
        if request.proposed_cost > limit:
            decision = "ESCALATE"
            escalation_reasons.append(f"Proposed cost (RM {request.proposed_cost:,.2f}) exceeds spend threshold (RM {limit:,.2f})")

    return {
        "decision": decision,
        "escalation_reasons": escalation_reasons,
        "timestamp": datetime.datetime.now().isoformat()
    }


# ==========================================
# AI Wizard Endpoints (ai_router)
# ==========================================

@ai_router.post("")
@ai_router.post("/")
async def create_ai_policy(policy: PolicyCreateSchema, db: Session = Depends(get_db)):
    print("🚨 DIAGNOSTIC HIT: POST /api/ai/policies (AI Wizard Save)")
    return await create_policy(policy, db)


@ai_router.post("/analyze-input")
async def analyze_input(request: AnalyzeInputRequest):
    print(f"🧠 DIAGNOSTIC HIT: POST /api/ai/policies/analyze-input with input: {request.input}")
    text_input = request.input.lower()
    suggested_type = "logical" if "$" in text_input or "under" in text_input else "natural_language"
    words = request.input.split()
    name = " ".join(words[:4]).title() + " Rule" if len(words) > 0 else "New AI Rule"

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
    print(f"🛡️ DIAGNOSTIC HIT: POST /api/ai/policies/check-conflicts for: {request.natural_language}")
    return {
        "conflicts": [],
        "overrides": [],
        "clarifications": [],
        "suggested_instructions": [],
        "refined_instruction": request.natural_language,
        "is_valid": True,
        "warnings": []
    }