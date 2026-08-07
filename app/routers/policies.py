
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
from app.core.database import get_db

# (Ensure your router prefix matches what the modal is hitting)
#router = APIRouter(prefix="/api/ai/policies", tags=["AI Policies"])
router = APIRouter(tags=["AI Policies"])


@router.patch("/{policy_id}")
@router.patch("/{policy_id}/")
async def update_policy(
    policy_id: str, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    print(f"\n📥 [POLICIES API] PATCH request received for Policy ID: {policy_id}")
    print(f"📦 [POLICIES API] Payload: {payload}")
    
    try:
        # 1. Check if the policy exists in the database
        query_check = text("SELECT * FROM policies WHERE id = :id")
        existing_policy = db.execute(query_check, {"id": policy_id}).fetchone()
        
        if not existing_policy:
            # Fallback check in case the ID was stored as an integer
            try:
                query_check_int = text("SELECT * FROM policies WHERE id = :id")
                existing_policy = db.execute(query_check_int, {"id": int(policy_id)}).fetchone()
                policy_id = int(policy_id)
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")

        # 2. Map the fields from the frontend payload to database column names
        # Note: Frontend uses camelCase or snake_case, let's map them defensively!
        update_fields = {}
        for key, val in payload.items():
            # Strip or map fields that shouldn't be updated or map format
            if key == "id" or val is None:
                continue
            update_fields[key] = val

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update.")

        # 3. Visually compile the dynamic update SQL statement
        set_clauses = [f"{col} = :{col}" for col in update_fields.keys()]
        query_update = text(f"""
            UPDATE policies 
            SET {', '.join(set_clauses)}
            WHERE id = :policy_id
        """)
        
        # Add the ID parameter to the binder
        update_fields["policy_id"] = policy_id
        
        # Execute the update query
        db.execute(query_update, update_fields)
        db.commit()
        
        print(f"✅ [POLICIES API] Policy {policy_id} updated successfully in Supabase!")
        
        # 4. Fetch and return the updated record to the frontend
        updated_record = db.execute(text("SELECT * FROM policies WHERE id = :id"), {"id": policy_id}).mappings().first()
        return dict(updated_record)

    except Exception as e:
        db.rollback()
        print(f"❌ [POLICIES API ERROR] Failed to update policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))