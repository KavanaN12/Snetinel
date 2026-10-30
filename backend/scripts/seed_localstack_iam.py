from __future__ import annotations

import argparse
import json
import uuid

import boto3

from src.modules.iam_analysis.remediation import LocalStackIamExecutor
from src.shared.config.settings import get_settings


def seed_scenario(scenario: str, endpoint_url: str) -> dict[str, object]:
    settings = get_settings()
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    iam = session.client("iam", endpoint_url=endpoint_url)
    LocalStackIamExecutor(iam, endpoint_url).check_ready()
    s3 = session.client("s3", endpoint_url=endpoint_url)
    account_id = session.client("sts", endpoint_url=endpoint_url).get_caller_identity()["Account"]

    suffix = uuid.uuid4().hex[:8]
    username = f"sentinel-vulnerable-{suffix}"
    bucket_name = f"sentinel-sensitive-{suffix}"
    role_names = (
        [f"sentinel-privileged-{suffix}"]
        if scenario == "single-role"
        else [f"sentinel-privileged-a-{suffix}", f"sentinel-privileged-b-{suffix}"]
    )
    user = iam.create_user(UserName=username)["User"]
    user_arn = user["Arn"]

    try:
        s3.create_bucket(Bucket=bucket_name)
    except s3.exceptions.BucketAlreadyOwnedByYou:
        pass
    s3.put_object(
        Bucket=bucket_name,
        Key="confidential/report.txt",
        Body=b"LocalStack-only SENTINEL scenario data",
    )

    role_arns = []
    for role_name in role_names:
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Principal": {"AWS": user_arn},
                "Action": "sts:AssumeRole",
            },
        }
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )["Role"]
        role_arn = role["Arn"]
        role_arns.append(role_arn)
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="SentinelScenarioDataAccess",
            PolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": {
                        "Effect": "Allow",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    },
                }
            ),
        )

    iam.put_user_policy(
        UserName=username,
        PolicyName="SentinelScenarioAssumeRole",
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": role_arns,
                },
            }
        ),
    )
    return {
        "scenario": scenario,
        "account_id": account_id,
        "user_name": username,
        "user_arn": user_arn,
        "role_arns": role_arns,
        "bucket_name": bucket_name,
        "bucket_arn": f"arn:aws:s3:::{bucket_name}",
        "expected_attack_path": (
            "IAM user -> trusted role -> S3 object access"
            if scenario == "single-role"
            else "IAM user -> either trusted role -> S3 object access"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a vulnerable IAM scenario in a verified LocalStack instance."
    )
    parser.add_argument(
        "--scenario",
        choices=("single-role", "adaptive"),
        default="single-role",
    )
    parser.add_argument(
        "--endpoint",
        default=get_settings().AWS_ENDPOINT_URL,
        help="LocalStack endpoint; must be http://localhost:4566 or compose service localstack:4566",
    )
    arguments = parser.parse_args()
    print(json.dumps(seed_scenario(arguments.scenario, arguments.endpoint), indent=2))


if __name__ == "__main__":
    main()
