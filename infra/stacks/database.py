"""Database Stack - Aurora Serverless v2 PostgreSQL."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Creates Aurora Serverless v2 PostgreSQL database."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Security group for database
        self.db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for Aurora database",
            allow_all_outbound=False,
        )

        # Database credentials in Secrets Manager
        self.db_secret = secretsmanager.Secret(
            self,
            "DatabaseSecret",
            secret_name="bluemoxon/db",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "bluemoxon_admin"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # Aurora Serverless v2 Cluster
        self.cluster = rds.DatabaseCluster(
            self,
            "BlueMoxonDatabase",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4,
            ),
            credentials=rds.Credentials.from_secret(self.db_secret),
            default_database_name="bluemoxon",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[self.db_security_group],
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=2,
            writer=rds.ClusterInstance.serverless_v2(
                "Writer",
                enable_performance_insights=True,
            ),
            backup=rds.BackupProps(
                retention=Duration.days(7),
            ),
            storage_encrypted=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
        )
