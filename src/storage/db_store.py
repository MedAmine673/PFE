import sqlite3
import os
from datetime import datetime

DB_PATH = "data/audit_history.db"

def init_db():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            tenant_name TEXT NOT NULL,
            audit_date TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            failed_controls INTEGER NOT NULL,
            total_controls INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_run_id INTEGER NOT NULL,
            control_id TEXT NOT NULL,
            category TEXT NOT NULL,
            requirement TEXT NOT NULL,
            result TEXT NOT NULL,
            criticality TEXT NOT NULL,
            risk_points INTEGER NOT NULL,
            affected INTEGER NOT NULL,
            details TEXT,
            FOREIGN KEY (audit_run_id) REFERENCES audit_runs(id)
        )
    """)
    conn.commit()
    conn.close()


def save_audit_to_db(tenant_id, tenant_name, report):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    summary = report.get("summary", {})
    findings = report.get("findings", [])

    cur.execute("""
        INSERT INTO audit_runs (
            tenant_id,
            tenant_name,
            audit_date,
            risk_score,
            risk_level,
            failed_controls,
            total_controls
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        tenant_id,
        tenant_name,
        datetime.now().isoformat(),
        summary.get("risk_score", 0),
        summary.get("risk_level", "N/A"),
        summary.get("failed_controls", 0),
        summary.get("total_controls", 0),
    ))

    audit_run_id = cur.lastrowid

    for finding in findings:
        cur.execute("""
            INSERT INTO audit_findings (
                audit_run_id,
                control_id,
                category,
                requirement,
                result,
                criticality,
                risk_points,
                affected,
                details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_run_id,
            finding.get("Control ID", ""),
            finding.get("Category", ""),
            finding.get("Requirement", ""),
            finding.get("Result", ""),
            finding.get("Criticality", ""),
            finding.get("Risk Points", 0),
            finding.get("Affected", 0),
            finding.get("Details", ""),
        ))

   
    conn.commit()
    conn.close()

def get_audit_runs_by_tenant(tenant_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, tenant_id, tenant_name, audit_date, risk_score, risk_level,
               failed_controls, total_controls
        FROM audit_runs
        WHERE tenant_name = ?
        ORDER BY audit_date DESC
    """, (tenant_name,))

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_audit_report_by_run_id(audit_run_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, tenant_id, tenant_name, audit_date, risk_score, risk_level,
               failed_controls, total_controls
        FROM audit_runs
        WHERE id = ?
    """, (audit_run_id,))
    run_row = cur.fetchone()

    if not run_row:
        conn.close()
        return None

    cur.execute("""
        SELECT control_id, category, requirement, result, criticality,
               risk_points, affected, details
        FROM audit_findings
        WHERE audit_run_id = ?
        ORDER BY id ASC
    """, (audit_run_id,))
    finding_rows = cur.fetchall()

    conn.close()

    summary = {
        "risk_score": run_row["risk_score"],
        "risk_level": run_row["risk_level"],
        "failed_controls": run_row["failed_controls"],
        "total_controls": run_row["total_controls"],
        "audit_date": run_row["audit_date"],
        "audit_run_id": run_row["id"],
    }

    findings = []
    for row in finding_rows:
        findings.append({
            "Control ID": row["control_id"],
            "Category": row["category"],
            "Requirement": row["requirement"],
            "Result": row["result"],
            "Criticality": row["criticality"],
            "Risk Points": row["risk_points"],
            "Affected": row["affected"],
            "Details": row["details"],
        })

    report = {
        "tenant": run_row["tenant_name"],
        "summary": summary,
        "findings": findings,
    }

    return report