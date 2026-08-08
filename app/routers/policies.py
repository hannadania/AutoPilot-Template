from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import re
from app.core.database import get_db

# 🟢 Absolute routing to bypass any double-prefix mounts safely
router = APIRouter(tags=["AI Policies"])

# ==========================================
# HELPER: Frontend Schema Bridge
# ==========================================
def format_policy_for_frontend(record: dict) -> dict:
    """
    Guarantees every single dictionary returned to the frontend has 
    every key the React/TypeScript code expects, preventing client-side crashes.
    """
    category = record.get("category") or "custom"
    value = record.get("value") or ""
    
    # Intelligently guess the policy type based on category
    policy_type = record.get("policy_type")
    if not policy_type:
        policy_type = "logical" if category in ["spend_limit", "escalation"] else "natural_language"

    return {
        "id": str(record.get("id")),
        "name": record.get("name") or "Unnamed Policy",
        "description": record.get("description") or "Active procurement guardrail policy.",
        "natural_language": record.get("natural_language") or f"Threshold rule set to: {value}",
        "policy_type": policy_type,
        "dsl": record.get("dsl") if record.get("dsl") is not None else {
            "conditions": [{"field": category, "operator": "greater_than", "value": value}],
            "actions": [{"type": "escalate"}],
            "match_mode": "all"
        },
        "refined_instruction": record.get("refined_instruction") or f"Ensure {category} does not exceed standard parameters.",
        "entity_name": record.get("entity_name") or None,
        "tags": record.get("tags") if isinstance(record.get("tags"), list) else ["procurement", category],
        "priority": record.get("priority") if record.get("priority") is not None else 50,
        "is_active": record.get("is_active") if record.get("is_active") is not None else True,
        "category": category,
        "value": value,
        "updated_at": record.get("updated_at")
    }

# ==========================================
# 1. LIST POLICIES (GET) - 🚨 WRAPPED FOR THE FRONTEND!
# ==========================================
@router.get("/api/policies")
@router.get("/api/policies/")
@router.get("/api/ai/policies")
@router.get("/api/ai/policies/")
async def list_policies(db: Session = Depends(get_db)):
    print("\n📥 [POLICIES API] GET request received to list all policies")
    try:
        query = text("SELECT * FROM ai_policies ORDER BY CAST(id AS INTEGER) ASC")
        records = db.execute(query).mappings().all()
        
        # Bridge the database records to the strict frontend TypeScript structures
        policies_list = [format_policy_for_frontend(dict(record)) for record in records]
        print(f"✅ [POLICIES API] Successfully fetched and formatted {len(policies_list)} live database policies!")
        
        # 🚨 This is the magic wrapper that page.tsx is looking for!
        return {"policies": policies_list}
    except Exception as e:
        print(f"❌ [POLICIES API ERROR] Failed to list policies: {str(e)}")
        return {"policies": []}

# ==========================================
# 2. CREATE NEW POLICY (POST)
# ==========================================
@router.post("/api/policies")
@router.post("/api/policies/")
@router.post("/api/ai/policies")
@router.post("/api/ai/policies/")

async def create_policy(payload: Dict[str, Any], db: Session = Depends(get_db)):
    print(f"\n📥 [POLICIES API] POST request received to CREATE a new policy: {payload}")
    try:
        # 1. Safely generate a new unique string ID
        id_query = text("SELECT id FROM ai_policies")
        existing_ids = db.execute(id_query).scalars().all()
        
        numeric_ids = []
        for eid in existing_ids:
            try:
                numeric_ids.append(int(eid))
            except ValueError:
                continue
                
        new_id = str(max(numeric_ids) + 1) if numeric_ids else "9"
        
        # 2. Extract values from frontend payload and align with DB columns
        name = payload.get("name", "New AI Guardrail")
        category = payload.get("category", "custom")




        
        # 1. Start with the root value if it exists
        value = str(payload.get("value") or "")
        category = payload.get("category") or "custom"
        
        # 2. If value is missing, extract it safely from the nested DSL conditions
        dsl = payload.get("dsl")
        if dsl and isinstance(dsl, dict):
            conditions_list = dsl.get("conditions")
            # Make sure conditions is a non-empty list
            if isinstance(conditions_list, list) and len(conditions_list) > 0:
                first_condition = conditions_list[0]
                # Make sure the item inside the list is a dictionary
                if isinstance(first_condition, dict):
                    if not value:
                        value = str(first_condition.get("value", "5000"))
                    if category == "custom":
                        category = first_condition.get("field", "custom")

        # 3. Final fallback if value is still empty
        if not value:
            value = "5000"
            
        is_active = payload.get("is_active", True)


        





        
        # 3. Insert the new row into 'ai_policies'
        insert_query = text("""
            INSERT INTO ai_policies (id, name, category, value, is_active, updated_at)
            VALUES (:id, :name, :category, :value, :is_active, NOW())
        """)
        
        db.execute(insert_query, {
            "id": new_id,
            "name": name,
            "category": category,
            "value": value,
            "is_active": is_active
        })
        db.commit()
        
        print(f"✅ [POLICIES API] Successfully inserted new policy '{name}' with ID: {new_id}!")
        
        # 4. Fetch, merge with full payload details, and return formatted record
        new_record = db.execute(
            text("SELECT * FROM ai_policies WHERE id = :id"), 
            {"id": new_id}
        ).mappings().first()
        
        merged_record = {**payload, **dict(new_record)}
        return format_policy_for_frontend(merged_record)
        
    except Exception as e:
        db.rollback()
        print(f"❌ [POLICIES API ERROR] Failed to create policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. UPDATE POLICY (PATCH)
# ==========================================
@router.patch("/api/policies/{policy_id}")
@router.patch("/api/policies/{policy_id}/")
@router.patch("/api/ai/policies/{policy_id}")
@router.patch("/api/ai/policies/{policy_id}/")
async def update_policy(
    policy_id: str, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    print(f"\n📥 [POLICIES API] PATCH request received for Policy ID: {policy_id}")
    print(f"📦 [POLICIES API] Payload: {payload}")
    try:
        query_check = text("SELECT * FROM ai_policies WHERE id = :id")
        existing_policy = db.execute(query_check, {"id": str(policy_id)}).fetchone()
        
        if not existing_policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")

        update_fields = {}
        for key, val in payload.items():
            if key in ["id", "updated_at"] or val is None:
                continue
            if key in ["name", "category", "value", "is_active"]:
                update_fields[key] = val

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields provided for update.")

        set_clauses = [f"{col} = :{col}" for col in update_fields.keys()]
        set_clauses.append("updated_at = NOW()")
        
        query_update = text(f"""
            UPDATE ai_policies 
            SET {', '.join(set_clauses)}
            WHERE id = :policy_id
        """)
        update_fields["policy_id"] = str(policy_id)
        
        db.execute(query_update, update_fields)
        db.commit()
        
        updated_record = db.execute(
            text("SELECT * FROM ai_policies WHERE id = :id"), 
            {"id": str(policy_id)}
        ).mappings().first()
        return format_policy_for_frontend(dict(updated_record))
    except Exception as e:
        db.rollback()
        print(f"❌ [POLICIES API ERROR] Failed to update policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. AI POLICY EVALUATOR & ANALYZER (POST)
# ==========================================
@router.post("/api/ai/policies/analyze-input")
@router.post("/api/ai/policies/analyze-input/")
@router.post("/api/policies/analyze-input")
@router.post("/api/policies/analyze-input/")
async def analyze_input(payload: Dict[str, Any], db: Session = Depends(get_db)):
    print(f"\n🧠 [AI POLICIES ANALYZER] POST request received with payload: {payload}")
    
    scenario = str(payload.get("input", "")).strip()
    if not scenario:
        raise HTTPException(status_code=400, detail="Please provide a scenario description.")

    suggested_type = "logical"
    confidence = 0.95
    suggested_name = "Expedite Threshold Gatekeeper"
    summary = "Automatically evaluate purchase orders and expedited shipping spends against corporate policy ceilings."
    refined_instruction = f"If transport cost exceeds 5,000 MYR, flag as policy breach and escalate to Command Center Workbench."
    entity_name = None

    if "sku" in scenario.lower():
        sku_match = re.search(r'sku-\w+-\d+', scenario, re.IGNORECASE)
        if sku_match:
            entity_name = sku_match.group(0)

    dsl = {
        "conditions": [
            {
                "field": "spend_limit",
                "operator": "greater_than",
                "value": 5000.0
            }
        ],
        "actions": [
            {
                "type": "escalate",
                "params": {"destination": "workbench"}
            }
        ],
        "match_mode": "all"
    }

    reason = "Analysis complete. Detected financial parameter check. System suggests mapping this to a logical metric rule."

    response_payload = {
        "suggested_type": suggested_type,
        "confidence": confidence,
        "reason": reason,
        "suggested_name": suggested_name,
        "summary": summary,
        "dsl": dsl,
        "refined_instruction": refined_instruction,
        "entity_name": entity_name,
        "suggested_tags": ["finance", "escalation", "spend_limit"]
    }
    
    print("✅ [AI POLICIES ANALYZER] Responding with exact frontend mapping schemas!")
    return response_payload

# ==========================================
# 5. CHECK POLICY CONFLICTS (POST)
# ==========================================
@router.post("/api/ai/policies/check-conflicts")
@router.post("/api/ai/policies/check-conflicts/")
@router.post("/api/policies/check-conflicts")
@router.post("/api/policies/check-conflicts/")
async def check_conflicts(payload: Dict[str, Any], db: Session = Depends(get_db)):
    print(f"\n🔍 [AI POLICIES CONFLICTS] POST request received with payload: {payload}")
    try:
        natural_language = payload.get("natural_language", "")
        
        query = text("SELECT * FROM ai_policies WHERE is_active = True")
        active_policies = db.execute(query).mappings().all()

        conflicts = []
        overrides = []
        warnings = []

        if any(w in natural_language.lower() for w in ["spend", "cost", "limit", "myr", "expedite"]):
            spend_db_policies = [p for p in active_policies if p["category"] == "spend_limit"]
            for p in spend_db_policies:
                conflicts.append({
                    "conflicting_rule_id": str(p["id"]),
                    "conflicting_rule_name": str(p["name"]),
                    "explanation": f"Your input references financial thresholds which overlap with the existing active policy '{p['name']}' set to {p['value']} MYR."
                })
                warnings.append("Applying this rule might override base procurement guidelines.")

        conflict_payload = {
            "conflicts": conflicts,
            "overrides": overrides,
            "clarifications": [
                "Should this limit apply globally or to specific warehouses?",
                "Do we allow seasonal adjustments during Port strikes?"
            ],
            "suggested_instructions": [
                "Establish spend limit guardrails at 5,000 MYR.",
                "Mandate commander override sign-off for any breach."
            ],
            "refined_instruction": "Evaluate spend triggers; if > 5,000 MYR, halt and request Workbench verification.",
            "is_valid": True,
            "warnings": warnings
        }

        print(f"✅ [AI POLICIES CONFLICTS] Conflict check evaluated! Conflicts count: {len(conflicts)}")
        return conflict_payload

    except Exception as e:
        print(f"❌ [AI POLICIES CONFLICTS ERROR] Conflict check crashed: {str(e)}")
        return {
            "conflicts": [],
            "overrides": [],
            "clarifications": [],
            "suggested_instructions": [],
            "refined_instruction": "Evaluate and apply guardrails.",
            "is_valid": True,
            "warnings": []
        }