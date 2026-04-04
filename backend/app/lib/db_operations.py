"""Neo4j database operations: connection management, query execution, graph registration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MERGE_KEYS: dict[str, list[str]] = {
    "Client": ["name"],
    "Supporter": ["name"],
    "NgAction": ["action"],
    "CarePreference": ["category", "instruction"],
    "Condition": ["name"],
    "KeyPerson": ["name"],
    "Organization": ["name"],
    "ServiceProvider": ["name"],
    "Hospital": ["name"],
    "Guardian": ["name"],
    "Certificate": ["type"],
}

ALLOWED_CREATE_LABELS: set[str] = {
    "SupportLog",
    "LifeHistory",
    "Wish",
    "AuditLog",
    "PublicAssistance",
    "MeetingRecord",
}

ALLOWED_LABELS: set[str] = set(MERGE_KEYS.keys()) | ALLOWED_CREATE_LABELS

ALLOWED_REL_TYPES: set[str] = {
    "HAS_CONDITION",
    "MUST_AVOID",
    "IN_CONTEXT",
    "REQUIRES",
    "ADDRESSES",
    "HAS_KEY_PERSON",
    "HAS_LEGAL_REP",
    "HAS_CERTIFICATE",
    "RECEIVES",
    "REGISTERED_AT",
    "TREATED_AT",
    "SUPPORTED_BY",
    "LOGGED",
    "ABOUT",
    "FOLLOWS",
    "USES_SERVICE",
    "HAS_HISTORY",
    "HAS_WISH",
    "AUDIT_FOR",
    "HAS_IDENTITY",
    "RECORDED",
}

# ---------------------------------------------------------------------------
# Driver singleton
# ---------------------------------------------------------------------------

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the singleton Neo4j driver, creating it on first call."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        logger.info("Neo4j driver created: %s", settings.neo4j_uri)
    return _driver


def close_driver() -> None:
    """Close and reset the singleton driver."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

def is_db_available() -> bool:
    """Return True if the Neo4j database is reachable."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception as exc:
        logger.warning("Neo4j connectivity check failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def run_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a Cypher query and return all records as a list of dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


# ---------------------------------------------------------------------------
# Node registration helpers
# ---------------------------------------------------------------------------

def _build_merge_query(label: str, keys: list[str]) -> str:
    """Build a MERGE query for a node with the given merge keys."""
    key_conditions = " AND ".join(f"n.{k} = ${k}" for k in keys)
    set_clause = ", ".join(f"n.{k} = ${k}" for k in keys)
    return (
        f"MERGE (n:{label} {{{', '.join(f'{k}: ${k}' for k in keys)}}})\n"
        f"ON CREATE SET n += $props\n"
        f"ON MATCH SET n += $props\n"
        f"RETURN n"
    )


def _register_node(
    session: Any,
    label: str,
    properties: dict,
) -> bool:
    """Register a single node; return True on success."""
    if label not in ALLOWED_LABELS:
        logger.warning("Skipping node with disallowed label: %r", label)
        return False

    props = {k: v for k, v in properties.items() if v is not None}

    if label in MERGE_KEYS:
        keys = MERGE_KEYS[label]
        # Ensure all merge keys are present
        missing = [k for k in keys if k not in props]
        if missing:
            logger.warning(
                "Skipping %s node — missing merge key(s): %s", label, missing
            )
            return False
        merge_props = {k: props[k] for k in keys}
        extra_props = {k: v for k, v in props.items() if k not in keys}
        cypher = (
            f"MERGE (n:{label} {{{', '.join(f'{k}: ${k}' for k in keys)}}})\n"
            f"ON CREATE SET n += $extra_props\n"
            f"ON MATCH SET n += $extra_props\n"
            f"RETURN n"
        )
        params = {**merge_props, "extra_props": extra_props}
        session.run(cypher, params)
    else:
        # CREATE-only labels
        cypher = f"CREATE (n:{label} $props) RETURN n"
        session.run(cypher, {"props": props})

    return True


def _register_relationship(
    session: Any,
    rel: dict,
) -> bool:
    """Register a single relationship; return True on success."""
    rel_type = rel.get("type")
    from_label = rel.get("from_label")
    from_key = rel.get("from_key")
    from_value = rel.get("from_value")
    to_label = rel.get("to_label")
    to_key = rel.get("to_key")
    to_value = rel.get("to_value")
    properties = rel.get("properties", {}) or {}

    if not all([rel_type, from_label, from_key, from_value, to_label, to_key, to_value]):
        logger.warning("Skipping incomplete relationship: %r", rel)
        return False

    if rel_type not in ALLOWED_REL_TYPES:
        logger.warning("Skipping relationship with disallowed type: %r", rel_type)
        return False

    if from_label not in ALLOWED_LABELS or to_label not in ALLOWED_LABELS:
        logger.warning(
            "Skipping relationship — disallowed label: from=%r to=%r",
            from_label, to_label,
        )
        return False

    cypher = (
        f"MATCH (a:{from_label} {{{from_key}: $from_value}})\n"
        f"MATCH (b:{to_label} {{{to_key}: $to_value}})\n"
        f"MERGE (a)-[r:{rel_type}]->(b)\n"
        f"ON CREATE SET r += $props\n"
        f"ON MATCH SET r += $props\n"
        f"RETURN r"
    )
    session.run(
        cypher,
        {"from_value": from_value, "to_value": to_value, "props": properties},
    )
    return True


# ---------------------------------------------------------------------------
# Main registration function
# ---------------------------------------------------------------------------

def register_to_database(
    extracted_graph: dict,
    user_name: str = "system",
) -> dict:
    """Register nodes and relationships from an extracted graph dict.

    Args:
        extracted_graph: Dict with optional keys ``nodes`` and ``relationships``.
        user_name: Name of the actor performing registration (used for audit log).

    Returns:
        Dict with keys:
        - ``status``: ``"success"`` or ``"error"``
        - ``client_name``: Name of the primary Client node (or ``None``)
        - ``registered_count``: Number of successfully registered nodes
        - ``registered_types``: List of node labels that were registered
        - ``error``: Error message (only present when status is ``"error"``)
    """
    nodes: list[dict] = extracted_graph.get("nodes", []) or []
    relationships: list[dict] = extracted_graph.get("relationships", []) or []

    client_name: str | None = None
    registered_count = 0
    registered_types: list[str] = []

    try:
        driver = get_driver()
        with driver.session() as session:
            # --- Register nodes ---
            for node in nodes:
                label = node.get("label", "")
                properties = node.get("properties", {}) or {}

                # Extract client name for the response
                if label == "Client" and "name" in properties:
                    client_name = properties["name"]

                if _register_node(session, label, properties):
                    registered_count += 1
                    if label not in registered_types:
                        registered_types.append(label)

            # --- Build temp_id map for source_temp_id/target_temp_id resolution ---
            temp_id_map = {}
            for node in nodes:
                temp_id = node.get("temp_id")
                if not temp_id:
                    continue
                label = node.get("label", "")
                props = node.get("properties", {}) or {}
                if label in MERGE_KEYS:
                    keys = MERGE_KEYS[label]
                    if keys and keys[0] in props:
                        temp_id_map[temp_id] = {
                            "label": label,
                            "key": keys[0],
                            "value": props[keys[0]],
                        }
                elif label in ALLOWED_CREATE_LABELS:
                    # For CREATE-only labels, use a unique property if available
                    for candidate_key in ["date", "id", "title", "filePath"]:
                        if candidate_key in props:
                            temp_id_map[temp_id] = {
                                "label": label,
                                "key": candidate_key,
                                "value": props[candidate_key],
                            }
                            break

            # --- Register relationships ---
            for rel in relationships:
                # Convert source_temp_id/target_temp_id to from_label/from_key/from_value format
                if "source_temp_id" in rel and "from_label" not in rel:
                    src = temp_id_map.get(rel["source_temp_id"])
                    tgt = temp_id_map.get(rel["target_temp_id"])
                    if src and tgt:
                        rel = {
                            "type": rel.get("type"),
                            "from_label": src["label"],
                            "from_key": src["key"],
                            "from_value": src["value"],
                            "to_label": tgt["label"],
                            "to_key": tgt["key"],
                            "to_value": tgt["value"],
                            "properties": rel.get("properties", {}),
                        }
                    else:
                        logger.warning("Cannot resolve temp_ids for relationship: %r", rel)
                        continue
                _register_relationship(session, rel)

            # --- Audit log ---
            if client_name:
                _create_audit_log_in_session(
                    session,
                    user_name=user_name,
                    action="register",
                    target_type="Client",
                    target_name=client_name,
                    details=f"Registered {registered_count} node(s): {registered_types}",
                    client_name=client_name,
                )

        return {
            "status": "success",
            "client_name": client_name,
            "registered_count": registered_count,
            "registered_types": registered_types,
        }

    except Exception as exc:
        logger.error("register_to_database failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "client_name": client_name,
            "registered_count": registered_count,
            "registered_types": registered_types,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _create_audit_log_in_session(
    session: Any,
    user_name: str,
    action: str,
    target_type: str,
    target_name: str,
    details: str,
    client_name: str,
) -> None:
    """Write an AuditLog node inside an existing session."""
    now = datetime.now(timezone.utc).isoformat()
    cypher = (
        "CREATE (a:AuditLog {"
        "  userName: $user_name,"
        "  action: $action,"
        "  targetType: $target_type,"
        "  targetName: $target_name,"
        "  details: $details,"
        "  createdAt: $created_at"
        "})\n"
        "WITH a\n"
        "MATCH (c:Client {name: $client_name})\n"
        "MERGE (a)-[:AUDIT_FOR]->(c)\n"
        "RETURN a"
    )
    session.run(
        cypher,
        {
            "user_name": user_name,
            "action": action,
            "target_type": target_type,
            "target_name": target_name,
            "details": details,
            "created_at": now,
            "client_name": client_name,
        },
    )


def create_audit_log(
    user_name: str,
    action: str,
    target_type: str,
    target_name: str,
    details: str,
    client_name: str,
) -> None:
    """Public helper to write an AuditLog node linked to a Client."""
    try:
        driver = get_driver()
        with driver.session() as session:
            _create_audit_log_in_session(
                session,
                user_name=user_name,
                action=action,
                target_type=target_type,
                target_name=target_name,
                details=details,
                client_name=client_name,
            )
    except Exception as exc:
        logger.error("create_audit_log failed: %s", exc, exc_info=True)
