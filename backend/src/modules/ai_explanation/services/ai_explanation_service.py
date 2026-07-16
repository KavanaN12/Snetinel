from __future__ import annotations

from typing import Any

from src.modules.ai_explanation.schemas.responses import AIExplanationResponse


class AIExplanationService:
    def __init__(self, provider: Any | None = None) -> None:
        self._provider = provider

    async def explain_finding(self, finding: dict[str, Any]) -> AIExplanationResponse:
        title = finding.get("title") or "Persisted finding"
        severity = (finding.get("severity") or "low").lower()
        attack_type = None
        evidence = finding.get("evidence_subgraph") or {}
        if isinstance(evidence, dict):
            attack_type = evidence.get("attack_type")
        affected = finding.get("affected_resource_ids") or []

        if self._provider is not None:
            try:
                summary = await self._provider.generate_text(
                    f"Explain the security finding {title} with severity {severity}.",
                    system_prompt="You are a concise security analyst.",
                )
                return AIExplanationResponse(
                    summary=summary,
                    details=[
                        "The explanation was generated through the configured provider.",
                        "No database changes were made during explanation generation.",
                    ],
                    confidence="high",
                    fallback_used=False,
                )
            except Exception:
                pass

        if title and attack_type and affected:
            summary = (
                f"High-severity finding: {title}. The persisted evidence shows {attack_type} across "
                f"{', '.join(map(str, affected))}."
            )
            if severity != "high":
                summary = summary.replace("High-severity", f"{severity.title()}-severity")
            return AIExplanationResponse(
                summary=summary,
                details=[
                    "The explanation is grounded in persisted evidence subgraph data.",
                    "No database changes were made during explanation generation.",
                ],
                confidence="high",
                fallback_used=False,
            )

        return AIExplanationResponse(
            summary="A deterministic fallback explanation was used because the finding payload was incomplete.",
            details=[
                "The fallback explanation uses available finding metadata only.",
                "No database changes were made during explanation generation.",
            ],
            confidence="medium",
            fallback_used=True,
        )
