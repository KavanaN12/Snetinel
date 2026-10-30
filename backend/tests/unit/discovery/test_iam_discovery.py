from src.modules.discovery.services.cloud_discovery_service import CloudDiscoveryService


class FakeIamClient:
    def list_users(self, Marker=None):
        if Marker:
            return {
                "Users": [
                    {
                        "UserName": "bob",
                        "UserId": "u-bob",
                        "Arn": "arn:aws:iam::123456789012:user/bob",
                    }
                ]
            }
        return {
            "Users": [
                {
                    "UserName": "alice",
                    "UserId": "u-alice",
                    "Arn": "arn:aws:iam::123456789012:user/alice",
                    "PermissionsBoundary": {
                        "PermissionsBoundaryArn": "arn:aws:iam::123456789012:policy/boundary"
                    },
                }
            ],
            "IsTruncated": True,
            "Marker": "second-page",
        }

    def list_attached_user_policies(self, UserName):
        return {
            "AttachedPolicies": [
                {"PolicyArn": f"arn:aws:iam::123456789012:policy/{UserName}-policy"}
            ]
        }

    def list_groups_for_user(self, UserName):
        return {"Groups": [{"GroupName": "security"}]} if UserName == "alice" else {"Groups": []}

    def list_user_policies(self, UserName):
        return {"PolicyNames": ["inline-read"]} if UserName == "alice" else {"PolicyNames": []}

    def get_user_policy(self, UserName, PolicyName):
        return {
            "PolicyDocument": {
                "Statement": {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::reports/*",
                }
            }
        }

    def list_policies(self, Scope, Marker=None):
        assert Scope == "Local"
        return {
            "Policies": [
                {
                    "PolicyName": "local-policy",
                    "PolicyId": "local-id",
                    "Arn": "arn:aws:iam::123456789012:policy/local-policy",
                    "DefaultVersionId": "v1",
                }
            ]
        }

    def get_policy(self, PolicyArn):
        return {
            "Policy": {
                "PolicyName": PolicyArn.rsplit("/", 1)[-1],
                "PolicyId": "managed-id",
                "Arn": PolicyArn,
                "DefaultVersionId": "v4",
            }
        }

    def get_policy_version(self, PolicyArn, VersionId):
        return {
            "PolicyVersion": {
                "Document": {
                    "Statement": {
                        "Effect": "Allow",
                        "Action": "s3:ListBucket",
                        "Resource": "arn:aws:s3:::reports",
                    }
                }
            }
        }


def test_iam_user_discovery_collects_policies_membership_boundary_and_pages() -> None:
    service = CloudDiscoveryService(None, None, None)

    users = service._discover_iam_users({"iam": FakeIamClient()})

    assert [user["resource_id"] for user in users] == ["alice", "bob"]
    alice = users[0]["details"]
    assert alice["attached_policy_arns"] == [
        "arn:aws:iam::123456789012:policy/alice-policy"
    ]
    assert alice["inline_policies"][0]["name"] == "inline-read"
    assert alice["inline_policies"][0]["document"]["Statement"]["Action"] == "s3:GetObject"
    assert alice["group_names"] == ["security"]
    assert alice["permissions_boundary_arn"] == "arn:aws:iam::123456789012:policy/boundary"


def test_managed_policy_documents_are_resolved_for_local_and_attached_policies() -> None:
    service = CloudDiscoveryService(None, None, None)
    attached_policy = "arn:aws:iam::123456789012:policy/attached-managed"
    resources = service._discover_iam_policies(
        {"iam": FakeIamClient()},
        [
            {
                "details": {
                    "attached_policy_arns": [attached_policy],
                    "permissions_boundary_arn": None,
                }
            }
        ],
    )

    assert {resource["resource_id"] for resource in resources} == {
        "arn:aws:iam::123456789012:policy/local-policy",
        attached_policy,
    }
    assert all(resource["details"]["document"]["Statement"] for resource in resources)


def test_scenario_discovery_filter_keeps_only_the_selected_run_manifest():
    resources = [
        {"resource_type": "iam_user", "resource_id": "scenario-user"},
        {"resource_type": "iam_role", "resource_id": "other-workspace-role"},
        {"resource_type": "s3_bucket", "resource_id": "scenario-bucket"},
        {"resource_type": "s3_bucket", "resource_id": "other-workspace-bucket"},
    ]
    manifest = {
        "resource_keys": [
            {"resource_type": "iam_user", "resource_id": "scenario-user"},
            {"resource_type": "s3_bucket", "resource_id": "scenario-bucket"},
        ]
    }

    filtered = CloudDiscoveryService._filter_scenario_resources(resources, manifest)

    assert filtered == [resources[0], resources[2]]
