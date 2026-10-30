from src.modules.iam_analysis.policy_evaluator import IamPolicyEvaluator


def statement(effect: str, action, resource="*", **extra):
    return {"Effect": effect, "Action": action, "Resource": resource, **extra}


def test_explicit_deny_overrides_an_allow() -> None:
    result = IamPolicyEvaluator().evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::sensitive/report.csv",
        policies=[
            {"Statement": statement("Allow", "s3:*")},
            {
                "Statement": statement(
                    "Deny",
                    "s3:GetObject",
                    "arn:aws:s3:::sensitive/*",
                    Sid="deny-sensitive",
                )
            },
        ],
    )

    assert result.decision == "EXPLICIT_DENY"
    assert not result.allowed
    assert result.matched_deny_statements == ("deny-sensitive",)


def test_not_action_and_not_resource_are_evaluated_as_complements() -> None:
    evaluator = IamPolicyEvaluator()
    policy = {
        "Statement": [
            {"Effect": "Allow", "NotAction": "iam:DeleteUser", "Resource": "*"},
            {"Effect": "Deny", "Action": "s3:*", "NotResource": "arn:aws:s3:::public/*"},
        ]
    }

    assert evaluator.evaluate(
        action="iam:ListUsers", resource="*", policies=[policy]
    ).allowed
    assert not evaluator.evaluate(
        action="iam:DeleteUser", resource="*", policies=[policy]
    ).allowed
    assert evaluator.evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::public/file",
        policies=[policy],
    ).decision == "ALLOW"
    assert evaluator.evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::private/file",
        policies=[policy],
    ).decision == "EXPLICIT_DENY"


def test_conditions_cover_string_ip_and_numeric_operators() -> None:
    policy = {
        "Statement": statement(
            "Allow",
            "s3:GetObject",
            "arn:aws:s3:::reports/*",
            Condition={
                "StringEquals": {"aws:PrincipalTag/team": "security"},
                "IpAddress": {"aws:SourceIp": ["192.0.2.0/24"]},
                "NumericLessThanEquals": {"custom:Risk": "3"},
            },
        )
    }
    evaluator = IamPolicyEvaluator()

    allowed = evaluator.evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::reports/q1.csv",
        policies=[policy],
        context={
            "aws:PrincipalTag/team": "security",
            "aws:SourceIp": "192.0.2.17",
            "custom:Risk": 2,
        },
    )
    denied = evaluator.evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::reports/q1.csv",
        policies=[policy],
        context={
            "aws:PrincipalTag/team": "security",
            "aws:SourceIp": "198.51.100.4",
            "custom:Risk": 2,
        },
    )

    assert allowed.allowed
    assert denied.decision == "IMPLICIT_DENY"


def test_unknown_condition_operator_fails_closed_and_is_reported() -> None:
    policy = {
        "Statement": statement(
            "Allow",
            "s3:GetObject",
            Condition={"UnrecognizedOperator": {"custom:key": "value"}},
        )
    }

    result = IamPolicyEvaluator().evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::bucket/key",
        policies=[policy],
        context={"custom:key": "value"},
    )

    assert result.decision == "IMPLICIT_DENY"
    assert result.unsupported_conditions == ("UnrecognizedOperator",)


def test_permission_boundary_intersects_identity_permissions() -> None:
    evaluator = IamPolicyEvaluator()
    identity_policy = {"Statement": statement("Allow", "s3:*")}
    read_only_boundary = {"Statement": statement("Allow", "s3:GetObject")}

    read = evaluator.evaluate(
        action="s3:GetObject",
        resource="arn:aws:s3:::bucket/key",
        policies=[identity_policy],
        permission_boundaries=[read_only_boundary],
    )
    write = evaluator.evaluate(
        action="s3:PutObject",
        resource="arn:aws:s3:::bucket/key",
        policies=[identity_policy],
        permission_boundaries=[read_only_boundary],
    )

    assert read.allowed and read.boundary_applied
    assert write.decision == "BOUNDARY_DENY"


def test_role_trust_requires_matching_principal_action_and_condition() -> None:
    trust = {
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:role/analyst"},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": "sentinel-test"}},
            }
        ]
    }
    evaluator = IamPolicyEvaluator()

    accepted = evaluator.evaluate_trust(
        trust_policy=trust,
        principal="arn:aws:iam::123456789012:role/analyst",
        context={"sts:ExternalId": "sentinel-test"},
    )
    wrong_external_id = evaluator.evaluate_trust(
        trust_policy=trust,
        principal="arn:aws:iam::123456789012:role/analyst",
        context={"sts:ExternalId": "wrong"},
    )
    wrong_principal = evaluator.evaluate_trust(
        trust_policy=trust,
        principal="arn:aws:iam::123456789012:user/analyst",
        context={"sts:ExternalId": "sentinel-test"},
    )

    assert accepted.allowed
    assert wrong_external_id.decision == "IMPLICIT_DENY"
    assert wrong_principal.decision == "IMPLICIT_DENY"


def test_missing_request_context_is_reported_as_indeterminate() -> None:
    trust = {
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"sts:ExternalId": "expected"}},
        }
    }

    result = IamPolicyEvaluator().evaluate_trust(
        trust_policy=trust,
        principal="arn:aws:iam::123456789012:user/alice",
    )

    assert result.decision == "INDETERMINATE"
    assert result.missing_context_keys == ("sts:ExternalId",)


def test_cross_account_access_requires_identity_and_resource_policy_allows() -> None:
    evaluator = IamPolicyEvaluator()
    principal = "arn:aws:iam::111111111111:user/alice"
    bucket = "arn:aws:s3:::shared-data"
    identity_policy = {"Statement": statement("Allow", "s3:GetObject", f"{bucket}/*")}
    resource_policy = {
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": principal},
            "Action": "s3:GetObject",
            "Resource": f"{bucket}/*",
        }
    }

    allowed = evaluator.evaluate(
        action="s3:GetObject",
        resource=f"{bucket}/report.csv",
        policies=[identity_policy],
        resource_policies=[resource_policy],
        principal_arn=principal,
        cross_account=True,
    )
    missing_resource_grant = evaluator.evaluate(
        action="s3:GetObject",
        resource=f"{bucket}/report.csv",
        policies=[identity_policy],
        resource_policies=[],
        principal_arn=principal,
        cross_account=True,
    )
    missing_resource_policy = evaluator.evaluate(
        action="s3:GetObject",
        resource=f"{bucket}/report.csv",
        policies=[identity_policy],
        principal_arn=principal,
        cross_account=True,
    )

    assert allowed.allowed
    assert missing_resource_grant.decision == "IMPLICIT_DENY"
    assert missing_resource_policy.decision == "INDETERMINATE"
    assert missing_resource_policy.missing_evidence == ("cross_account_resource_policy",)


def test_resource_policy_explicit_deny_overrides_identity_allow() -> None:
    bucket = "arn:aws:s3:::private-data"
    principal = "arn:aws:iam::123456789012:user/alice"
    result = IamPolicyEvaluator().evaluate(
        action="s3:GetObject",
        resource=f"{bucket}/secret.csv",
        policies=[{"Statement": statement("Allow", "s3:GetObject", f"{bucket}/*")}],
        resource_policies=[
            {
                "Statement": {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"{bucket}/*",
                }
            }
        ],
        principal_arn=principal,
        cross_account=False,
    )

    assert result.decision == "EXPLICIT_DENY"
    assert result.matched_deny_statements == ("policy[0].statement[0]",)
