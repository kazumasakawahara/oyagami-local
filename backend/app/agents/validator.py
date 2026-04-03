"""Validator Agent — schema validation and safety compliance checking."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from app.config import settings
from app.lib.db_operations import ALLOWED_LABELS, ALLOWED_REL_TYPES, MERGE_KEYS, run_query
from app.schemas.narrative import SafetyCheckResult, ValidationResult

logger = logging.getLogger(__name__)
PROMPT_DIR = Path(__file__).parent / "prompts"


def get_safety_prompt() -> str:
    """Load safety compliance prompt from file."""
    return (PROMPT_DIR / "safety.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def validate_schema(graph: dict) -> ValidationResult:
    """Validate extracted graph against Neo4j schema.

    Checks:
    - Node labels are in ALLOWED_LABELS
    - Relationship types are in ALLOWED_REL_TYPES
    - Required merge key properties are present for MERGE_KEYS labels
    - temp_id references in relationships are consistent (warn on dangling refs)

    Returns ValidationResult(is_valid, errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    nodes = graph.get("nodes", [])
    relationships = graph.get("relationships", [])

    # Collect all declared temp_ids for reference checking
    declared_temp_ids: set[str] = set()

    for node in nodes:
        label = node.get("label", "")
        temp_id = node.get("temp_id", "")
        properties = node.get("properties", {})

        if temp_id:
            declared_temp_ids.add(temp_id)

        # Check label is allowed
        if label not in ALLOWED_LABELS:
            errors.append(
                f"Node '{temp_id}' has disallowed label '{label}'. "
                f"Allowed labels: {sorted(ALLOWED_LABELS)}"
            )
            continue

        # Check required merge key properties are present
        if label in MERGE_KEYS:
            required_keys = MERGE_KEYS[label]
            missing_keys = [k for k in required_keys if k not in properties or properties[k] is None]
            if missing_keys:
                errors.append(
                    f"Node '{temp_id}' (label='{label}') is missing required "
                    f"merge key(s): {missing_keys}"
                )

    for rel in relationships:
        rel_type = rel.get("type", "")
        source_id = rel.get("source_temp_id", "")
        target_id = rel.get("target_temp_id", "")

        # Check relationship type is allowed
        if rel_type not in ALLOWED_REL_TYPES:
            errors.append(
                f"Relationship from '{source_id}' to '{target_id}' has disallowed "
                f"type '{rel_type}'. Allowed types: {sorted(ALLOWED_REL_TYPES)}"
            )

        # Warn on dangling temp_id references
        if source_id and source_id not in declared_temp_ids:
            warnings.append(
                f"Relationship type '{rel_type}' references unknown source temp_id '{source_id}'"
            )
        if target_id and target_id not in declared_temp_ids:
            warnings.append(
                f"Relationship type '{rel_type}' references unknown target temp_id '{target_id}'"
            )

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Safety compliance check
# ---------------------------------------------------------------------------


async def check_safety_compliance(
    narrative: str, client_name: str | None
) -> SafetyCheckResult:
    """Check narrative text against existing NgActions for a client.

    If no client_name is provided, returns a safe result immediately.
    Otherwise, fetches NgActions from Neo4j and uses mistral-small to check
    for violations using the safety.md prompt.

    Returns SafetyCheckResult(is_violation, warning, risk_level).
    """
    if not client_name:
        return SafetyCheckResult(is_violation=False, warning=None, risk_level="None")

    # Fetch existing NgActions for client from Neo4j
    try:
        records = run_query(
            """
            MATCH (c:Client {name: $name})-[:MUST_AVOID]->(ng:NgAction)
            RETURN ng.action AS action, ng.riskLevel AS riskLevel, ng.note AS note
            """,
            {"name": client_name},
        )
    except Exception as exc:
        logger.warning("Failed to fetch NgActions for '%s': %s", client_name, exc)
        return SafetyCheckResult(is_violation=False, warning=None, risk_level="None")

    if not records:
        return SafetyCheckResult(is_violation=False, warning=None, risk_level="None")

    # Format NgActions for the prompt
    ng_actions_text = "\n".join(
        f"- {r['action']} (リスクレベル: {r.get('riskLevel', 'Unknown')})"
        + (f" — {r['note']}" if r.get("note") else "")
        for r in records
    )

    prompt_template = get_safety_prompt()
    system_prompt = prompt_template.replace("{ng_actions}", ng_actions_text).replace(
        "{narrative}", narrative
    )

    try:
        async with httpx.AsyncClient(
            base_url=settings.ollama_base_url, timeout=60
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={
                    "model": settings.validator_model,
                    "messages": [
                        {"role": "user", "content": system_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            result_data = _parse_safety_response(content)
            if result_data:
                return SafetyCheckResult(
                    is_violation=result_data.get("is_violation", False),
                    warning=result_data.get("warning"),
                    risk_level=result_data.get("risk_level", "None"),
                )
    except Exception as exc:
        logger.error("Safety compliance check failed: %s", exc)

    return SafetyCheckResult(is_violation=False, warning=None, risk_level="None")


def _parse_safety_response(response_text: str) -> dict | None:
    """Extract JSON safety result from LLM response."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
