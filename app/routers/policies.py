from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import datetime

router = APIRouter(prefix="/api/policies", tags=["Policies"])

class PolicyUpdate(BaseModel):
    is_active: bool
    value: Optional[Dict[str, Any]] = None

FULL_POLICIES = [
    {
        "id": "expedite-spend-limit",
        "name": "Expedite Spend Limit ($50k)",
        "description": "Requires executive sign-off for freight expedites exceeding $50,000.",
        "natural_language": "If expedite cost exceeds $50,000, trigger executive approval workflow.",
        "summary": "Financial guardrail for emergency shipping costs.",
        "policy_type": "logical",
        "dsl": {"conditions": [{"field": "expedite_cost", "operator": "greater_than", "value": "50000"}], "actions": [{"type": "require_approval", "value": "VP"}], "match_mode": "all"},
        "refined_instruction": None,
        "ai_instruction": "WHEN expedite_cost > 50000 THEN require_approval(VP)",
        "entity_name": "shipment",
        "is_active": True,
        "priority": 1,
        "tags": ["finance", "expedite", "round2"],
        "execution_count": 12,
        "last_executed_at": datetime.datetime.utcnow().isoformat(),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    },
    {
        "id": "tier1-customer-priority",
        "name": "Strict Tier-1 Customer Priority",
        "description": "Automatically reallocate inventory from Tier-2/3 orders to fulfill Tier-1 delays.",
        "natural_language": "When Tier-1 customer orders face inventory shortages, automatically reallocate from lower tiers.",
        "summary": "Protects high-value customer SLAs during stockouts.",
        "policy_type": "logical",
        "dsl": {"conditions": [{"field": "customer_tier", "operator": "equals", "value": "1"}], "actions": [{"type": "priority_allocation"}], "match_mode": "all"},
        "refined_instruction": None,
        "ai_instruction": "WHEN customer_tier = 1 AND stockout = true THEN prioritize_reallocation",
        "entity_name": "order",
        "is_active": True,
        "priority": 2,
        "tags": ["customer", "reallocation", "round2"],
        "execution_count": 28,
        "last_executed_at": datetime.datetime.utcnow().isoformat(),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    },
    {
        "id": "penalty-clause-escalation",
        "name": "Contract Penalty Auto-Escalation",
        "description": "Escalates directly to Workbench if late delivery penalty exceeds $10,000.",
        "natural_language": "If estimated shipment delay incurs contract penalty over $10,000, route exception to Human Workbench.",
        "summary": "Human-in-the-loop requirement for costly contract penalties.",
        "policy_type": "natural_language",
        "dsl": None,
        "refined_instruction": "On shipment delay: calculate penalty. If penalty > $10,000, pause operator and alert Workbench.",
        "ai_instruction": "On shipment delay: calculate penalty. If penalty > $10,000, pause operator and alert Workbench.",
        "entity_name": "penalty",
        "is_active": True,
        "priority": 3,
        "tags": ["legal", "penalties", "workbench"],
        "execution_count": 5,
        "last_executed_at": datetime.datetime.utcnow().isoformat(),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
]

@router.get("")
async def get_policies():
    """Returns active Round 2 AI policies under the 'policies' key."""
    return {"status": "success", "policies": FULL_POLICIES}

@router.put("/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate):
    """Updates policy toggle status live."""
    for policy in FULL_POLICIES:
        if policy["id"] == policy_id:
            policy["is_active"] = payload.is_active
            policy["updated_at"] = datetime.datetime.utcnow().isoformat()
            return {"status": "updated", "policy": policy}
            
    raise HTTPException(status_code=404, detail="Policy not found")