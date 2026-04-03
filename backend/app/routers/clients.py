"""Clients router — client list, detail, emergency info, and support logs."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.lib.db_operations import run_query
from app.lib.utils import calculate_age
from app.schemas.client import (
    CarePreference,
    ClientDetail,
    ClientSummary,
    EmergencyInfo,
    KeyPerson,
    NgAction,
    SupportLogEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clients", tags=["clients"])


# ---------------------------------------------------------------------------
# GET /api/clients
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ClientSummary])
def list_clients(
    kana_prefix: str | None = Query(default=None, description="かな行頭文字でフィルタ（例: あ）"),
) -> list[ClientSummary]:
    """クライアント一覧を返す。kana_prefix が指定されれば kana フィールドで前方一致フィルタ。"""
    try:
        rows = run_query(
            """
            MATCH (c:Client)
            OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cond:Condition)
            RETURN c.name AS name,
                   c.dob AS dob,
                   c.bloodType AS blood_type,
                   c.kana AS kana,
                   collect(DISTINCT cond.name) AS conditions
            ORDER BY c.name
            """
        )

        summaries: list[ClientSummary] = []
        for row in rows:
            kana: str | None = row.get("kana")
            if kana_prefix and (not kana or not kana.startswith(kana_prefix)):
                continue

            dob = row.get("dob")
            age = calculate_age(dob) if dob else None
            conditions = [c for c in (row.get("conditions") or []) if c]
            summaries.append(
                ClientSummary(
                    name=row["name"],
                    dob=str(dob) if dob else None,
                    age=age,
                    blood_type=row.get("blood_type"),
                    conditions=conditions,
                )
            )
        return summaries

    except Exception as exc:
        logger.error("list_clients failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/clients/{name}
# ---------------------------------------------------------------------------


@router.get("/{name}", response_model=ClientDetail)
def get_client(name: str) -> ClientDetail:
    """クライアントの詳細プロフィールを返す（関連ノードすべて含む）。"""
    try:
        # Basic info + conditions
        base_rows = run_query(
            """
            MATCH (c:Client {name: $name})
            OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cond:Condition)
            RETURN c.name AS name, c.dob AS dob, c.bloodType AS blood_type,
                   collect(DISTINCT {name: cond.name, diagnosedDate: cond.diagnosedDate}) AS conditions
            """,
            {"name": name},
        )
        if not base_rows:
            raise HTTPException(status_code=404, detail=f"Client '{name}' not found")

        row = base_rows[0]
        dob = row.get("dob")
        age = calculate_age(dob) if dob else None

        # NgActions
        ng_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:MUST_AVOID]->(ng:NgAction)
            RETURN ng.action AS action, ng.reason AS reason, ng.riskLevel AS risk_level
            ORDER BY
              CASE ng.riskLevel
                WHEN 'LifeThreatening' THEN 1
                WHEN 'Panic' THEN 2
                ELSE 3
              END
            """,
            {"name": name},
        )
        ng_actions = [
            NgAction(
                action=r["action"],
                reason=r.get("reason"),
                risk_level=r.get("risk_level") or "Discomfort",
            )
            for r in ng_rows
        ]

        # CarePreferences
        care_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:REQUIRES]->(cp:CarePreference)
            RETURN cp.category AS category, cp.instruction AS instruction, cp.priority AS priority
            """,
            {"name": name},
        )
        care_preferences = [
            CarePreference(
                category=r["category"],
                instruction=r["instruction"],
                priority=r.get("priority"),
            )
            for r in care_rows
        ]

        # KeyPersons
        kp_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[rel:HAS_KEY_PERSON]->(kp:KeyPerson)
            RETURN kp.name AS kp_name, kp.relationship AS relationship,
                   kp.phone AS phone, rel.rank AS rank
            ORDER BY rel.rank ASC
            """,
            {"name": name},
        )
        key_persons = [
            KeyPerson(
                name=r["kp_name"],
                relationship=r.get("relationship"),
                phone=r.get("phone"),
                rank=r.get("rank"),
            )
            for r in kp_rows
        ]

        # Certificates
        cert_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:HAS_CERTIFICATE]->(cert:Certificate)
            RETURN cert {.*} AS cert
            """,
            {"name": name},
        )
        certificates = [r["cert"] for r in cert_rows]

        # Hospital
        hosp_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:TREATED_AT]->(h:Hospital)
            RETURN h {.*} AS hospital
            LIMIT 1
            """,
            {"name": name},
        )
        hospital = hosp_rows[0]["hospital"] if hosp_rows else None

        # Guardian
        guardian_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:HAS_LEGAL_REP]->(g:Guardian)
            RETURN g {.*} AS guardian
            LIMIT 1
            """,
            {"name": name},
        )
        guardian = guardian_rows[0]["guardian"] if guardian_rows else None

        conditions = [c for c in (row.get("conditions") or []) if c.get("name")]

        return ClientDetail(
            name=row["name"],
            dob=str(dob) if dob else None,
            age=age,
            blood_type=row.get("blood_type"),
            conditions=conditions,
            ng_actions=ng_actions,
            care_preferences=care_preferences,
            key_persons=key_persons,
            certificates=certificates,
            hospital=hospital,
            guardian=guardian,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_client failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/clients/{name}/emergency
# ---------------------------------------------------------------------------


@router.get("/{name}/emergency", response_model=EmergencyInfo)
def get_emergency(name: str) -> EmergencyInfo:
    """緊急時情報を返す（NgAction 優先度順、Safety First）。"""
    try:
        # Verify client exists
        exists = run_query("MATCH (c:Client {name: $name}) RETURN c.name AS n LIMIT 1", {"name": name})
        if not exists:
            raise HTTPException(status_code=404, detail=f"Client '{name}' not found")

        # NgActions (life-threatening first)
        ng_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:MUST_AVOID]->(ng:NgAction)
            RETURN ng.action AS action, ng.reason AS reason, ng.riskLevel AS risk_level
            ORDER BY
              CASE ng.riskLevel
                WHEN 'LifeThreatening' THEN 1
                WHEN 'Panic' THEN 2
                ELSE 3
              END
            """,
            {"name": name},
        )
        ng_actions = [
            NgAction(
                action=r["action"],
                reason=r.get("reason"),
                risk_level=r.get("risk_level") or "Discomfort",
            )
            for r in ng_rows
        ]

        # CarePreferences
        care_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:REQUIRES]->(cp:CarePreference)
            RETURN cp.category AS category, cp.instruction AS instruction, cp.priority AS priority
            """,
            {"name": name},
        )
        care_preferences = [
            CarePreference(
                category=r["category"],
                instruction=r["instruction"],
                priority=r.get("priority"),
            )
            for r in care_rows
        ]

        # KeyPersons
        kp_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[rel:HAS_KEY_PERSON]->(kp:KeyPerson)
            RETURN kp.name AS kp_name, kp.relationship AS relationship,
                   kp.phone AS phone, rel.rank AS rank
            ORDER BY rel.rank ASC
            """,
            {"name": name},
        )
        key_persons = [
            KeyPerson(
                name=r["kp_name"],
                relationship=r.get("relationship"),
                phone=r.get("phone"),
                rank=r.get("rank"),
            )
            for r in kp_rows
        ]

        # Hospital
        hosp_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:TREATED_AT]->(h:Hospital)
            RETURN h {.*} AS hospital
            LIMIT 1
            """,
            {"name": name},
        )
        hospital = hosp_rows[0]["hospital"] if hosp_rows else None

        # Guardian
        guardian_rows = run_query(
            """
            MATCH (c:Client {name: $name})-[:HAS_LEGAL_REP]->(g:Guardian)
            RETURN g {.*} AS guardian
            LIMIT 1
            """,
            {"name": name},
        )
        guardian = guardian_rows[0]["guardian"] if guardian_rows else None

        return EmergencyInfo(
            client_name=name,
            ng_actions=ng_actions,
            care_preferences=care_preferences,
            key_persons=key_persons,
            hospital=hospital,
            guardian=guardian,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_emergency failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/clients/{name}/logs
# ---------------------------------------------------------------------------


@router.get("/{name}/logs", response_model=list[SupportLogEntry])
def get_logs(name: str, limit: int = Query(default=50, ge=1, le=200)) -> list[SupportLogEntry]:
    """クライアントの支援記録を返す（デフォルト 50 件）。"""
    try:
        exists = run_query("MATCH (c:Client {name: $name}) RETURN c.name AS n LIMIT 1", {"name": name})
        if not exists:
            raise HTTPException(status_code=404, detail=f"Client '{name}' not found")

        rows = run_query(
            """
            MATCH (s:Supporter)-[:LOGGED]->(sl:SupportLog)-[:ABOUT]->(c:Client {name: $name})
            RETURN sl.date AS date,
                   sl.situation AS situation,
                   sl.action AS action,
                   sl.effectiveness AS effectiveness,
                   sl.note AS note,
                   s.name AS supporter_name
            ORDER BY sl.date DESC
            LIMIT $limit
            """,
            {"name": name, "limit": limit},
        )

        return [
            SupportLogEntry(
                date=str(r.get("date", "")) or None,
                situation=r.get("situation"),
                action=r.get("action"),
                effectiveness=r.get("effectiveness"),
                note=r.get("note"),
                supporter_name=r.get("supporter_name"),
            )
            for r in rows
        ]

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_logs failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
