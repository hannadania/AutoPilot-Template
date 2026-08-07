from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

# Import database session getter
from app.core.database import get_db

router = APIRouter(prefix="/api/insights", tags=["AI Insights"])

def run_query_with_fallback(db: Session, query_template: str, table_candidates: List[str], multiple_tables: bool = False):
    """
    Tries each table candidate in the query template until one succeeds.
    Safely rolls back transactions on failure to keep the Postgres block clean.
    """
    for table in table_candidates:
        try:
            if multiple_tables:
                sql_text = query_template.format(*table)
            else:
                sql_text = query_template.format(table=table)
                
            result = db.execute(text(sql_text))
            return result
        except Exception:
            db.rollback()  # Instantly heal the transaction state
            continue
    raise ValueError(f"All table candidates failed for template.")

@router.get("/summary")
async def get_supply_chain_insights(db: Session = Depends(get_db)):
    """
    Unified analytics endpoint. Auto-detects table names and casing
    to serve live Supabase records gracefully without breaking transactions.
    """
    debug_info = {}

    # -------------------------------------------------------------
    # KPI 1 & 2: Active POs & Value at Risk
    # -------------------------------------------------------------
    active_pos = 0
    value_at_risk_raw = 0.0
    try:
        po_query = "SELECT COUNT(*), COALESCE(SUM(po_total), 0) FROM {table} WHERE status = 'issued'"
        po_candidates = ["purchase_order_headers", '"purchase_order_headers_(1)"', '"purchase_order_headers (1)"']
        res = run_query_with_fallback(db, po_query, po_candidates).first()
        if res:
            active_pos = int(res[0])
            value_at_risk_raw = float(res[1])
            debug_info["kpi_po"] = "Success"
    except Exception as e:
        debug_info["kpi_po"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # KPI 3: Delayed Shipments
    # -------------------------------------------------------------
    delayed_shipments = 0
    try:
        delay_query = "SELECT COUNT(*) FROM {table} WHERE status IN ('delayed', 'at_risk')"
        delay_candidates = ["order_confirmations", '"order_confirmations_(1)"', '"order_confirmations (1)"']
        delayed_shipments = run_query_with_fallback(db, delay_query, delay_candidates).scalar() or 0
        debug_info["kpi_delays"] = "Success"
    except Exception as e:
        debug_info["kpi_delays"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # KPI 4: Sole Source Risks
    # -------------------------------------------------------------
    sole_sources = 0
    try:
        sole_query = "SELECT COUNT(*) FROM {table} WHERE LOWER(CAST(x_sole_source AS VARCHAR)) IN ('true', '1', 't', 'yes', 'y')"
        sole_candidates = ["suppliers", '"suppliers_(1)"', '"suppliers (1)"']
        sole_sources = run_query_with_fallback(db, sole_query, sole_candidates).scalar() or 0
        debug_info["kpi_sole_sources"] = "Success"
    except Exception as e:
        debug_info["kpi_sole_sources"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # INSIGHT 1: Single Source Exposure List
    # -------------------------------------------------------------
    sole_source_list = []
    try:
        sole_list_query = "SELECT id, name, country, x_tier FROM {table} WHERE LOWER(CAST(x_sole_source AS VARCHAR)) IN ('true', '1', 't', 'yes', 'y') LIMIT 5"
        sole_candidates = ["suppliers", '"suppliers_(1)"', '"suppliers (1)"']
        rows = run_query_with_fallback(db, sole_list_query, sole_candidates).mappings().all()
        sole_source_list = [dict(row) for row in rows]
        debug_info["insight_sole_sources"] = "Success"
    except Exception as e:
        debug_info["insight_sole_sources"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # INSIGHT 2: Supplier Delay Patterns
    # -------------------------------------------------------------
    delay_patterns = []
    try:
        delay_patterns_query = """
            SELECT S.name as supplier_name, COUNT(OC.id) as delay_count, OC.delay_reason
            FROM {0} OC
            JOIN {1} S ON CAST(OC.supplier_id AS VARCHAR) = CAST(S.id AS VARCHAR)
            WHERE OC.status IN ('delayed', 'at_risk')
            GROUP BY S.name, OC.delay_reason
            ORDER BY delay_count DESC
            LIMIT 5
        """
        combo_candidates = [
            ("order_confirmations", "suppliers"),
            ('"order_confirmations_(1)"', '"suppliers_(1)"'),
            ('"order_confirmations (1)"', '"suppliers (1)"')
        ]
        rows = run_query_with_fallback(db, delay_patterns_query, combo_candidates, multiple_tables=True).mappings().all()
        delay_patterns = [dict(row) for row in rows]
        debug_info["insight_delays"] = "Success"
    except Exception as e:
        debug_info["insight_delays"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # INSIGHT 3: Cascading Tier-2 Risks
    # -------------------------------------------------------------
    dependencies_list = []
    try:
        tier_query = """
            SELECT ST.id, ST.component, ST.criticality, 
                   S1.name as parent_supplier, S2.name as dependent_supplier
            FROM {0} ST
            JOIN {1} S1 ON CAST(ST.parent_supplier_id AS VARCHAR) = CAST(S1.id AS VARCHAR)
            JOIN {1} S2 ON CAST(ST.depends_on_supplier_id AS VARCHAR) = CAST(S2.id AS VARCHAR)
            WHERE ST.criticality IN ('critical', 'high')
            LIMIT 5
        """
        combo_candidates = [
            ("supplier_tiers", "suppliers"),
            ('"Supplier_Tiers"', "suppliers"),
            ('"Supplier_Tiers_(1)"', '"suppliers_(1)"'),
            ('"supplier_tiers_(1)"', '"suppliers_(1)"')
        ]
        rows = run_query_with_fallback(db, tier_query, combo_candidates, multiple_tables=True).mappings().all()
        dependencies_list = [dict(row) for row in rows]
        debug_info["insight_tier_dependencies"] = "Success"
    except Exception as e:
        debug_info["insight_tier_dependencies"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # INSIGHT 4: Demand Anomalies
    # -------------------------------------------------------------
    demand_spikes = []
    try:
        demand_spikes_query = """
            SELECT item_number, forecast_qty, actual_demand, channel,
                   (actual_demand - forecast_qty) as surge_qty
            FROM {table}
            WHERE actual_demand > forecast_qty
            ORDER BY surge_qty DESC
            LIMIT 5
        """
        ds_candidates = ["demand_signals", '"demand_signals_(1)"', '"demand_signals (1)"']
        rows = run_query_with_fallback(db, demand_spikes_query, ds_candidates).mappings().all()
        demand_spikes = [dict(row) for row in rows]
        debug_info["insight_demand"] = "Success"
    except Exception as e:
        debug_info["insight_demand"] = f"Failed: {str(e)}"

    # -------------------------------------------------------------
    # INSIGHT 5: Vulnerable Contract Expirations
    # -------------------------------------------------------------
    expiring_contracts = []
    try:
        expiring_contracts_query = """
            SELECT contract_number, name as contract_name, end_date, status
            FROM {table}
            WHERE status = 'published' AND end_date <= '2027-01-01'
            ORDER BY end_date ASC
            LIMIT 5
        """
        con_candidates = ["contracts", '"contracts_(1)"', '"contracts (1)"']
        rows = run_query_with_fallback(db, expiring_contracts_query, con_candidates).mappings().all()
        expiring_contracts = [dict(row) for row in rows]
        debug_info["insight_contracts"] = "Success"
    except Exception as e:
        debug_info["insight_contracts"] = f"Failed: {str(e)}"

    return {
        "status": "success",
        "kpis": {
            "active_pos": active_pos,
            "value_at_risk": f"RM {value_at_risk_raw:,.2f}",
            "delayed_shipments": delayed_shipments,
            "sole_sources": sole_sources
        },
        "insights": {
            "single_source_exposure": sole_source_list,
            "supplier_delay_patterns": delay_patterns,
            "tier_dependency_cascades": dependencies_list,
            "demand_anomalies": demand_spikes,
            "expiring_contracts": expiring_contracts
        },
        "debug_info": debug_info
    }