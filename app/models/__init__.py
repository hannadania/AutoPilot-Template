

# app/models/__init__.py

from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base
import datetime
from .audit import AuditCategory, AuditLog, AuditSeverity
from .item import Item
from .settings import Settings

__all__ = ["Item", "Settings", "AuditLog", "AuditCategory", "AuditSeverity"]




class PendingTask(Base):
    __tablename__ = "pending_tasks"

    # Match your SERIAL PRIMARY KEY (integer autoincrement)
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Match the exact columns your webhook receiver inserts
    run_id = Column(String, nullable=False)
    operator_name = Column(String, nullable=False)
    item_number = Column(String, nullable=False, index=True)
    proposed_action = Column(String, nullable=False)
    cost_impact = Column(String, nullable=False)
    jira_ticket_url = Column(String, nullable=False)
    
    # Default status to map to your 'PENDING' state
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)