from __future__ import annotations

from typing import Any

from src.modules.drift.domain.entities import DriftEvent
from src.modules.drift.repositories.drift_event_repository import DriftEventRepository


class DriftDetectionService:
    def __init__(self, drift_event_repository: DriftEventRepository) -> None:
        self._drift_event_repository = drift_event_repository

    async def detect_drift(self, workspace_id: str, current_user_id: str, previous_resources: list[Any], latest_resources: list[Any]) -> list[DriftEvent]:
        del current_user_id
        previous_map = {resource.resource_id: resource for resource in previous_resources}
        latest_map = {resource.resource_id: resource for resource in latest_resources}

        events: list[DriftEvent] = []
        for resource_id in sorted(set(latest_map) - set(previous_map)):
            event = await self._drift_event_repository.create_event(
                workspace_id=workspace_id,
                event_type="added",
                resource_type=latest_map[resource_id].resource_type,
                resource_id=resource_id,
                previous_value=None,
                current_value={"name": latest_map[resource_id].name, "details": getattr(latest_map[resource_id], "details", {})},
            )
            events.append(self._coerce_event(event))

        for resource_id in sorted(set(previous_map) - set(latest_map)):
            event = await self._drift_event_repository.create_event(
                workspace_id=workspace_id,
                event_type="removed",
                resource_type=previous_map[resource_id].resource_type,
                resource_id=resource_id,
                previous_value={"name": previous_map[resource_id].name, "details": getattr(previous_map[resource_id], "details", {})},
                current_value=None,
            )
            events.append(self._coerce_event(event))

        for resource_id in sorted(set(previous_map) & set(latest_map)):
            previous_resource = previous_map[resource_id]
            latest_resource = latest_map[resource_id]
            if getattr(previous_resource, "name", None) != getattr(latest_resource, "name", None) or getattr(previous_resource, "details", None) != getattr(latest_resource, "details", None):
                removed_event = await self._drift_event_repository.create_event(
                    workspace_id=workspace_id,
                    event_type="removed",
                    resource_type=previous_resource.resource_type,
                    resource_id=resource_id,
                    previous_value={"name": getattr(previous_resource, "name", None), "details": getattr(previous_resource, "details", {})},
                    current_value=None,
                )
                events.append(self._coerce_event(removed_event))

                modified_event = await self._drift_event_repository.create_event(
                    workspace_id=workspace_id,
                    event_type="modified",
                    resource_type=latest_resource.resource_type,
                    resource_id=resource_id,
                    previous_value={"name": getattr(previous_resource, "name", None), "details": getattr(previous_resource, "details", {})},
                    current_value={"name": getattr(latest_resource, "name", None), "details": getattr(latest_resource, "details", {})},
                )
                events.append(self._coerce_event(modified_event))

        return events

    def _coerce_event(self, event: object) -> DriftEvent:
        if isinstance(event, DriftEvent):
            return event
        if isinstance(event, dict):
            return DriftEvent(
                id=event.get("id"),
                workspace_id=event.get("workspace_id"),
                event_type=event.get("event_type", "added"),
                resource_type=event.get("resource_type", ""),
                resource_id=event.get("resource_id", ""),
                previous_value=event.get("previous_value"),
                current_value=event.get("current_value"),
                created_at=event.get("created_at"),
            )
        return DriftEvent(
            id=getattr(event, "id", None),
            workspace_id=getattr(event, "workspace_id", None),
            event_type=getattr(event, "event_type", "added"),
            resource_type=getattr(event, "resource_type", ""),
            resource_id=getattr(event, "resource_id", ""),
            previous_value=getattr(event, "previous_value", None),
            current_value=getattr(event, "current_value", None),
            created_at=getattr(event, "created_at", None),
        )
