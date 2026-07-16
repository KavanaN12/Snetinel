from types import SimpleNamespace

import pytest

from src.modules.drift.services.drift_detection_service import DriftDetectionService


class StubDriftEventRepository:
    def __init__(self):
        self.events = []

    async def create_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs

    async def list_for_workspace(self, workspace_id):
        return [event for event in self.events if event["workspace_id"] == workspace_id]


@pytest.mark.asyncio
async def test_detect_drift_reports_added_removed_and_modified_resources():
    service = DriftDetectionService(drift_event_repository=StubDriftEventRepository())
    previous = [
        SimpleNamespace(resource_type="s3", resource_id="bucket-a", name="old-bucket", details={"region": "us-east-1"}),
    ]
    latest = [
        SimpleNamespace(resource_type="s3", resource_id="bucket-b", name="new-bucket", details={"region": "us-east-2"}),
        SimpleNamespace(resource_type="s3", resource_id="bucket-a", name="old-bucket-renamed", details={"region": "us-east-1"}),
    ]

    result = await service.detect_drift("workspace-1", "user-1", previous, latest)

    assert any(event.event_type == "added" for event in result)
    assert any(event.event_type == "removed" for event in result)
    assert any(event.event_type == "modified" for event in result)
