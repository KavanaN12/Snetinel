from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import unquote


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    decision: str
    allowed: bool
    matched_allow_statements: tuple[str, ...] = ()
    matched_deny_statements: tuple[str, ...] = ()
    boundary_applied: bool = False
    unsupported_conditions: tuple[str, ...] = ()
    missing_context_keys: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()


@dataclass(slots=True)
class _PolicyResult:
    allows: list[str] = field(default_factory=list)
    denies: list[str] = field(default_factory=list)
    unsupported_conditions: set[str] = field(default_factory=set)
    missing_context_keys: set[str] = field(default_factory=set)


class IamPolicyEvaluator:
    """Conservative evaluator for AWS IAM identity and role-trust policies.

    Unknown condition operators fail closed and are surfaced in the result.
    This evaluator handles policy documents supplied by discovery; it does not
    infer permissions from policy names or represent AWS service-side state
    that was not collected.
    """

    def evaluate(
        self,
        *,
        action: str,
        resource: str,
        policies: list[dict[str, Any]],
        permission_boundaries: list[dict[str, Any]] | None = None,
        resource_policies: list[dict[str, Any]] | None = None,
        principal_arn: str | None = None,
        cross_account: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyEvaluation:
        identity = self._evaluate_policies(
            policies,
            action=action,
            resource=resource,
            context=context,
        )
        boundary_applied = permission_boundaries is not None
        boundary = (
            self._evaluate_policies(
                permission_boundaries,
                action=action,
                resource=resource,
                context=context,
            )
            if permission_boundaries is not None
            else None
        )
        resource_result = (
            self._evaluate_policies(
                resource_policies,
                action=action,
                resource=resource,
                context=context,
                principal=principal_arn,
            )
            if resource_policies is not None
            else None
        )
        missing_evidence: set[str] = set()
        if resource_result is not None and principal_arn is None:
            missing_evidence.add("principal_arn")
        if cross_account is None and principal_arn:
            principal_account = self._account_id(principal_arn)
            resource_account = self._account_id(resource)
            if principal_account and resource_account:
                cross_account = principal_account != resource_account

        denies = (
            identity.denies
            + (boundary.denies if boundary else [])
            + (resource_result.denies if resource_result else [])
        )
        unsupported = identity.unsupported_conditions | (
            boundary.unsupported_conditions if boundary else set()
        ) | (resource_result.unsupported_conditions if resource_result else set())
        missing_context = identity.missing_context_keys | (
            boundary.missing_context_keys if boundary else set()
        ) | (resource_result.missing_context_keys if resource_result else set())
        allows = identity.allows + (resource_result.allows if resource_result else [])
        if denies:
            return PolicyEvaluation(
                decision="EXPLICIT_DENY",
                allowed=False,
                matched_allow_statements=tuple(allows),
                matched_deny_statements=tuple(denies),
                boundary_applied=boundary_applied,
                unsupported_conditions=tuple(sorted(unsupported)),
                missing_context_keys=tuple(sorted(missing_context)),
                missing_evidence=tuple(sorted(missing_evidence)),
            )
        if cross_account is True and resource_result is None:
            missing_evidence.add("cross_account_resource_policy")
            return PolicyEvaluation(
                decision="INDETERMINATE",
                allowed=False,
                matched_allow_statements=tuple(identity.allows),
                boundary_applied=boundary_applied,
                unsupported_conditions=tuple(sorted(unsupported)),
                missing_context_keys=tuple(sorted(missing_context)),
                missing_evidence=tuple(sorted(missing_evidence)),
            )
        if cross_account is True:
            is_allowed = bool(identity.allows and resource_result and resource_result.allows)
        else:
            is_allowed = bool(identity.allows or (resource_result and resource_result.allows))
        if not is_allowed:
            return PolicyEvaluation(
                decision="INDETERMINATE" if missing_context else "IMPLICIT_DENY",
                allowed=False,
                matched_allow_statements=tuple(allows),
                boundary_applied=boundary_applied,
                unsupported_conditions=tuple(sorted(unsupported)),
                missing_context_keys=tuple(sorted(missing_context)),
                missing_evidence=tuple(sorted(missing_evidence)),
            )
        if boundary is not None and not boundary.allows:
            return PolicyEvaluation(
                decision="INDETERMINATE" if boundary.missing_context_keys else "BOUNDARY_DENY",
                allowed=False,
                matched_allow_statements=tuple(allows),
                boundary_applied=True,
                unsupported_conditions=tuple(sorted(unsupported)),
                missing_context_keys=tuple(sorted(missing_context)),
                missing_evidence=tuple(sorted(missing_evidence)),
            )
        return PolicyEvaluation(
            decision="ALLOW",
            allowed=True,
            matched_allow_statements=tuple(allows),
            boundary_applied=boundary_applied,
            unsupported_conditions=tuple(sorted(unsupported)),
            missing_context_keys=tuple(sorted(missing_context)),
            missing_evidence=tuple(sorted(missing_evidence)),
        )

    def evaluate_trust(
        self,
        *,
        trust_policy: dict[str, Any],
        principal: str,
        action: str = "sts:AssumeRole",
        context: dict[str, Any] | None = None,
    ) -> PolicyEvaluation:
        result = self._evaluate_policies(
            [trust_policy],
            action=action,
            resource="*",
            context=context,
            principal=principal,
            resource_required=False,
        )
        if result.denies:
            decision = "EXPLICIT_DENY"
        elif result.allows:
            decision = "ALLOW"
        elif result.missing_context_keys:
            decision = "INDETERMINATE"
        else:
            decision = "IMPLICIT_DENY"
        return PolicyEvaluation(
            decision=decision,
            allowed=decision == "ALLOW",
            matched_allow_statements=tuple(result.allows),
            matched_deny_statements=tuple(result.denies),
            unsupported_conditions=tuple(sorted(result.unsupported_conditions)),
            missing_context_keys=tuple(sorted(result.missing_context_keys)),
        )

    @staticmethod
    def _account_id(arn: str) -> str | None:
        parts = arn.split(":")
        return parts[4] if len(parts) > 4 and parts[4] else None

    @staticmethod
    def parse_document(document: Any) -> dict[str, Any] | None:
        if isinstance(document, dict):
            return document
        if not isinstance(document, str):
            return None
        for candidate in (document, unquote(document)):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _evaluate_policies(
        self,
        policies: list[dict[str, Any]] | None,
        *,
        action: str,
        resource: str,
        context: dict[str, Any] | None,
        principal: str | None = None,
        resource_required: bool = True,
    ) -> _PolicyResult:
        result = _PolicyResult()
        for policy_index, policy in enumerate(policies or []):
            parsed_policy = self.parse_document(policy)
            if parsed_policy is None:
                continue
            policy = parsed_policy
            if "document" in policy and isinstance(policy.get("document"), (dict, str)):
                policy = self.parse_document(policy["document"])
                if policy is None:
                    continue
            statements = policy.get("Statement", [])
            if isinstance(statements, dict):
                statements = [statements]
            if not isinstance(statements, list):
                continue
            for statement_index, statement in enumerate(statements):
                if not isinstance(statement, dict):
                    continue
                unsupported: set[str] = set()
                missing_context: set[str] = set()
                if not self._statement_matches(
                    statement,
                    action=action,
                    resource=resource,
                    context=context,
                    principal=principal,
                    resource_required=resource_required,
                    unsupported_conditions=unsupported,
                    missing_context_keys=missing_context,
                ):
                    result.unsupported_conditions.update(unsupported)
                    result.missing_context_keys.update(missing_context)
                    continue
                result.unsupported_conditions.update(unsupported)
                result.missing_context_keys.update(missing_context)
                statement_id = str(
                    statement.get("Sid", f"policy[{policy_index}].statement[{statement_index}]")
                )
                effect = statement.get("Effect")
                if effect == "Deny":
                    result.denies.append(statement_id)
                elif effect == "Allow":
                    result.allows.append(statement_id)
        return result

    def _statement_matches(
        self,
        statement: dict[str, Any],
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
        principal: str | None,
        resource_required: bool,
        unsupported_conditions: set[str],
        missing_context_keys: set[str],
    ) -> bool:
        if not self._matches_action(statement, action):
            return False
        if resource_required and not self._matches_resource(statement, resource):
            return False
        if principal is not None and not self._matches_principal(statement, principal):
            return False
        return self._matches_conditions(
            statement.get("Condition"),
            context,
            unsupported_conditions,
            missing_context_keys,
        )

    @staticmethod
    def _as_values(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value is None:
            return []
        return [str(value)]

    @classmethod
    def _matches_action(cls, statement: dict[str, Any], action: str) -> bool:
        if "Action" in statement:
            patterns = cls._as_values(statement.get("Action"))
            return bool(patterns) and any(
                cls._wildcard_matches(action.casefold(), pattern.casefold())
                for pattern in patterns
            )
        if "NotAction" in statement:
            excluded = cls._as_values(statement.get("NotAction"))
            return bool(excluded) and not any(
                cls._wildcard_matches(action.casefold(), pattern.casefold())
                for pattern in excluded
            )
        return False

    @classmethod
    def _matches_resource(cls, statement: dict[str, Any], resource: str) -> bool:
        if "Resource" in statement:
            patterns = cls._as_values(statement.get("Resource"))
            return bool(patterns) and any(
                cls._wildcard_matches(resource, pattern) for pattern in patterns
            )
        if "NotResource" in statement:
            excluded = cls._as_values(statement.get("NotResource"))
            return bool(excluded) and not any(
                cls._wildcard_matches(resource, pattern) for pattern in excluded
            )
        return False

    @classmethod
    def _matches_principal(cls, statement: dict[str, Any], principal: str) -> bool:
        if "Principal" in statement:
            return cls._principal_value_matches(statement["Principal"], principal)
        if "NotPrincipal" in statement:
            return not cls._principal_value_matches(statement["NotPrincipal"], principal)
        return False

    @classmethod
    def _principal_value_matches(cls, value: Any, principal: str) -> bool:
        if value == "*":
            return True
        if isinstance(value, dict):
            values = [item for entries in value.values() for item in cls._as_values(entries)]
        else:
            values = cls._as_values(value)
        return any(cls._principal_pattern_matches(principal, pattern) for pattern in values)

    @staticmethod
    def _principal_pattern_matches(principal: str, pattern: str) -> bool:
        normalized_principal = principal.casefold()
        normalized_pattern = pattern.casefold()
        if IamPolicyEvaluator._wildcard_matches(normalized_principal, normalized_pattern):
            return True
        pattern_parts = pattern.split(":")
        principal_parts = principal.split(":")
        return (
            len(pattern_parts) == 6
            and len(principal_parts) == 6
            and pattern_parts[0].casefold() == "arn"
            and pattern_parts[2].casefold() == "iam"
            and pattern_parts[5].casefold() == "root"
            and [part.casefold() for part in principal_parts[:5]]
            == [part.casefold() for part in pattern_parts[:5]]
            and principal_parts[5].casefold().startswith(("user/", "role/"))
        )

    @staticmethod
    def _wildcard_matches(value: str, pattern: str) -> bool:
        expression = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
        return re.fullmatch(expression, value, flags=re.DOTALL) is not None

    @classmethod
    def _matches_conditions(
        cls,
        conditions: Any,
        context: dict[str, Any] | None,
        unsupported_conditions: set[str],
        missing_context_keys: set[str],
    ) -> bool:
        if conditions is None:
            return True
        if not isinstance(conditions, dict):
            return False
        if context is None:
            missing_context_keys.update(
                str(key)
                for entries in conditions.values()
                if isinstance(entries, dict)
                for key in entries
            )
            return False
        context_values = {str(key).casefold(): value for key, value in context.items()}

        for operator, entries in conditions.items():
            if not isinstance(entries, dict):
                return False
            for key, expected in entries.items():
                exists = str(key).casefold() in context_values
                actual = context_values.get(str(key).casefold())
                if not cls._condition_matches(
                    str(operator),
                    actual,
                    expected,
                    exists,
                    unsupported_conditions,
                ):
                    return False
        return True

    @classmethod
    def _condition_matches(
        cls,
        operator: str,
        actual: Any,
        expected: Any,
        exists: bool,
        unsupported_conditions: set[str],
    ) -> bool:
        quantifier = None
        base_operator = operator
        if ":" in base_operator:
            quantifier, base_operator = base_operator.split(":", 1)

        if_exists = base_operator.endswith("IfExists")
        if if_exists:
            base_operator = base_operator[:-8]
        if not exists:
            if base_operator == "Null":
                expected_values = [value.casefold() for value in cls._as_values(expected)]
                return "true" in expected_values
            if if_exists or quantifier == "ForAllValues":
                return True
            return cls._is_negated_operator(base_operator)

        if base_operator == "Null":
            expected_values = [value.casefold() for value in cls._as_values(expected)]
            return "false" in expected_values

        compare = cls._comparison_for(base_operator)
        if compare is None:
            unsupported_conditions.add(operator)
            return False

        actual_values = actual if isinstance(actual, list) else [actual]
        expected_values = cls._as_values(expected)
        if not expected_values:
            return False

        negated = cls._is_negated_operator(base_operator)
        value_matches = [
            any(compare(str(actual_value), expected_value) for expected_value in expected_values)
            for actual_value in actual_values
        ]
        if negated:
            value_matches = [not matches for matches in value_matches]
        if quantifier == "ForAllValues":
            return bool(actual_values) and all(value_matches)
        if quantifier == "ForAnyValue":
            return any(value_matches)
        return all(value_matches) if negated else any(value_matches)

    @staticmethod
    def _is_negated_operator(operator: str) -> bool:
        return (
            operator.startswith("StringNot")
            or operator.startswith("ArnNot")
            or operator in {"NumericNotEquals", "DateNotEquals"}
            or operator in {"NotIpAddress", "NotIpAddressIfExists"}
        )

    @classmethod
    def _comparison_for(cls, operator: str):
        if operator in {"StringEquals", "ArnEquals"}:
            return lambda actual, expected: actual == expected
        if operator in {"StringNotEquals", "ArnNotEquals"}:
            return lambda actual, expected: actual == expected
        if operator in {"StringLike", "ArnLike"}:
            return lambda actual, expected: cls._wildcard_matches(actual, expected)
        if operator in {"StringNotLike", "ArnNotLike"}:
            return lambda actual, expected: cls._wildcard_matches(actual, expected)
        if operator in {"Bool", "BoolIfExists"}:
            return lambda actual, expected: actual.casefold() == expected.casefold()
        if operator in {"IpAddress", "NotIpAddress"}:
            return lambda actual, expected: cls._ip_matches(actual, expected, negate=False)
        if operator.startswith("Numeric"):
            if operator == "NumericNotEquals":
                return lambda actual, expected: cls._numeric_matches(
                    "NumericEquals", actual, expected
                )
            return lambda actual, expected: cls._numeric_matches(operator, actual, expected)
        if operator.startswith("Date"):
            if operator == "DateNotEquals":
                return lambda actual, expected: cls._date_matches(
                    "DateEquals", actual, expected
                )
            return lambda actual, expected: cls._date_matches(operator, actual, expected)
        return None

    @staticmethod
    def _ip_matches(actual: str, expected: str, *, negate: bool) -> bool:
        try:
            matches = ipaddress.ip_address(actual) in ipaddress.ip_network(expected, strict=False)
        except ValueError:
            return False
        return not matches if negate else matches

    @staticmethod
    def _numeric_matches(operator: str, actual: str, expected: str) -> bool:
        try:
            actual_value = Decimal(actual)
            expected_value = Decimal(expected)
        except InvalidOperation:
            return False
        if not actual_value.is_finite() or not expected_value.is_finite():
            return False
        return {
            "NumericEquals": actual_value == expected_value,
            "NumericNotEquals": actual_value != expected_value,
            "NumericLessThan": actual_value < expected_value,
            "NumericLessThanEquals": actual_value <= expected_value,
            "NumericGreaterThan": actual_value > expected_value,
            "NumericGreaterThanEquals": actual_value >= expected_value,
        }.get(operator, False)

    @staticmethod
    def _date_matches(operator: str, actual: str, expected: str) -> bool:
        def parse(value: str) -> datetime:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        try:
            actual_date, expected_date = parse(actual), parse(expected)
        except ValueError:
            return False
        if actual_date.tzinfo is None or expected_date.tzinfo is None:
            return False
        return {
            "DateEquals": actual_date == expected_date,
            "DateNotEquals": actual_date != expected_date,
            "DateLessThan": actual_date < expected_date,
            "DateLessThanEquals": actual_date <= expected_date,
            "DateGreaterThan": actual_date > expected_date,
            "DateGreaterThanEquals": actual_date >= expected_date,
        }.get(operator, False)
