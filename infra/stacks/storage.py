"""Storage Stack - S3 buckets for frontend and images."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
)
from constructs import Construct


class StorageStack(Stack):
    """Creates S3 buckets for frontend assets and book images."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Frontend bucket (SPA assets)
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"bluemoxon-frontend-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Images bucket (book photos)
        self.images_bucket = s3.Bucket(
            self,
            "ImagesBucket",
            bucket_name=f"bluemoxon-images-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                    ],
                    allowed_origins=["*"],  # Will be restricted in production
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Backup bucket
        self.backup_bucket = s3.Bucket(
            self,
            "BackupBucket",
            bucket_name=f"bluemoxon-backups-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="MoveToGlacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        ),
                    ],
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )
