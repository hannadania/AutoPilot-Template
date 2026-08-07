from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
from app.core.database import get_db

# 🟢 Keep the prefix aligned with your frontend
router = APIRouter(prefix="/api/policies", tags=["AI Policies"])

@router.get("")
@router.get("/")
async def list_policies(db: Session = Depends(get_db)):
    print("\n📥 [POLICIES API] GET request received to list all policies")
    try:
        # 1. Query all live policies from Supabase PostgreSQL database
        query = text("SELECT * FROM policies ORDER BY priority ASC, created_at DESC")
        records = db.execute(query).mappings().all()
        
        # 2. Convert database mappings to a list of dictionaries
        policies_list = [dict(record) for record in records]
        print(f"✅ [POLICIES API] Successfully fetched {len(policies_list)} live database policies!")
        return policies_list
        
    except Exception as e:
        print(f"❌ [POLICIES API ERROR] Failed to list policies: {str(e)}")
        # Safe fallback so your screen doesn't turn blank or crash if database is sleepy
        return []

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
        update_fields = {}
        for key, val in payload.items():
            # Strip fields that shouldn't be updated or are null
            if key == "id" or val is None:
                continue
            update_fields[key] = val

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update.")

        # 3. Compile the dynamic SQL update statement
        set_clauses = [f"{col} = :{col}" for col in update_fields.keys()]
        query_update = text(f"""
            UPDATE policies 
            SET {', '.join(set_clauses)}
            WHERE id = :policy_id
        """)
        
        # Add the ID parameter
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