import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(tags=["Webhooks"])

SUPERVITY_API_BASE = os.getenv("SUPERVITY_API_BASE", "https://auto.supervity.ai").rstrip("/")


class SupervityApprovalPayload(BaseModel):
    run_id: str
    operator_name: str
    item_number: str
    proposed_action: str
    cost_impact: str
    jira_ticket_url: str
    # Supervity sends camelCase; accept both shapes.
    activity_run_id: str | None = None
    activityRunId: str | None = None

    @property
    def resolved_activity_run_id(self) -> str | None:
        return self.activity_run_id or self.activityRunId


def _ensure_pending_tasks_table(db: Session) -> None:
    db.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS pending_tasks (
            id SERIAL PRIMARY KEY,
            run_id TEXT NOT NULL,
            activity_run_id TEXT,
            operator_name TEXT NOT NULL,
            item_number TEXT NOT NULL,
            proposed_action TEXT NOT NULL,
            cost_impact TEXT NOT NULL,
            jira_ticket_url TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """
        )
    )
    db.execute(
        text(
            "ALTER TABLE pending_tasks ADD COLUMN IF NOT EXISTS activity_run_id TEXT;"
        )
    )


async def _resume_supervity_hitl(activity_run_id: str) -> dict:
    """
    Supervity human-in-the-loop resume — public endpoint, no Bearer token.

    Docs: POST /api/v1/user-forms/:activityRunId/:status  (status = approve | reject)
    """
    url = f"{SUPERVITY_API_BASE}/api/v1/user-forms/{activity_run_id}/approve"
    log.info("Supervity HITL resume: POST %s (no auth)", url)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, timeout=15.0)
    except httpx.RequestError as exc:
        log.exception("Supervity resume request failed for activity_run_id=%s", activity_run_id)
        return {
            "ok": False,
            "status_code": None,
            "body": str(exc),
            "url": url,
            "error": "connection_failed",
        }

    body_preview = response.text[:1000] if response.text else ""
    log.info(
        "Supervity HITL response: activity_run_id=%s status=%s body=%s",
        activity_run_id,
        response.status_code,
        body_preview,
    )

    return {
        "ok": response.is_success,
        "status_code": response.status_code,
        "body": response.text,
        "url": url,
    }


@router.post("/supervity/workbench")
async def catch_ai_approval(payload: SupervityApprovalPayload, db: Session = Depends(get_db)):
    """
    Catches data from Supervity and queues it in your database.
    Final Path: POST /api/webhooks/supervity/workbench
    """
    _ensure_pending_tasks_table(db)

    activity_run_id = payload.resolved_activity_run_id
    log.info(
        "Workbench webhook: item=%s run_id=%s activity_run_id=%s operator=%s",
        payload.item_number,
        payload.run_id,
        activity_run_id,
        payload.operator_name,
    )

    insert_query = text(
        """
        INSERT INTO pending_tasks (
            run_id, activity_run_id, operator_name, item_number,
            proposed_action, cost_impact, jira_ticket_url, status
        )
        VALUES (:run_id, :activity_run_id, :op, :item, :action, :cost, :jira, 'PENDING')
    """
    )
    db.execute(
        insert_query,
        {
            "run_id": payload.run_id,
            "activity_run_id": activity_run_id,
            "op": payload.operator_name,
            "item": payload.item_number,
            "action": payload.proposed_action,
            "cost": payload.cost_impact,
            "jira": payload.jira_ticket_url,
        },
    )
    db.commit()
    return {"status": "success", "message": "Disruption routed to Workbench"}


@router.put("/supervity/workbench/{item_number}/approve")
async def approve_task(item_number: str, db: Session = Depends(get_db)):
    get_query = text(
        """
        SELECT run_id, activity_run_id FROM pending_tasks
        WHERE item_number = :item AND status = 'PENDING'
        ORDER BY created_at DESC LIMIT 1
    """
    )
    task = db.execute(get_query, {"item": item_number}).mappings().first()

    if not task:
        raise HTTPException(status_code=404, detail="No pending task found for this SKU")

    run_id = task["run_id"]
    activity_run_id = task["activity_run_id"] or run_id

    log.info(
        "Approve requested: item=%s run_id=%s activity_run_id=%s",
        item_number,
        run_id,
        task["activity_run_id"],
    )

    supervity_result = await _resume_supervity_hitl(activity_run_id)

    # Always clear locally so the workbench UI does not stay stuck.
    db.execute(
        text("UPDATE pending_tasks SET status = 'APPROVED' WHERE run_id = :rid"),
        {"rid": run_id},
    )
    db.commit()

    if supervity_result["ok"]:
        return {
            "status": "success",
            "message": f"Run {run_id} resumed on Supervity",
            "supervity": supervity_result,
        }

    log.warning(
        "Local task approved but Supervity resume failed: item=%s activity_run_id=%s result=%s",
        item_number,
        activity_run_id,
        supervity_result,
    )
    return {
        "status": "partial_success",
        "message": (
            "Task cleared locally, but Supervity did not resume. "
            "Check activity_run_id is a real Supervity UUID (not a test run_id)."
        ),
        "supervity": supervity_result,
    }
