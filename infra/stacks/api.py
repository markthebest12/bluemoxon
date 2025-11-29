"""API Stack - Lambda + API Gateway."""

from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_cognito as cognito,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
)
from constructs import Construct


class ApiStack(Stack):
    """Creates Lambda function and API Gateway for the backend."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        database_secret: secretsmanager.Secret,
        database_security_group: ec2.SecurityGroup,
        user_pool: cognito.UserPool,
        images_bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Security group for Lambda
        lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for API Lambda",
            allow_all_outbound=True,
        )

        # Allow Lambda to connect to Aurora
        database_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to connect to Aurora",
        )

        # Lambda function
        self.api_function = lambda_.Function(
            self,
            "ApiFunction",
            function_name="bluemoxon-api",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="app.main.handler",
            code=lambda_.Code.from_asset(
                "../backend",
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r app /asset-output/",
                    ],
                },
            ),
            memory_size=512,
            timeout=Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            security_groups=[lambda_security_group],
            environment={
                "DATABASE_SECRET_ARN": database_secret.secret_arn,
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "CORS_ORIGINS": "*",  # Will be restricted
            },
        )

        # Grant Lambda access to resources
        database_secret.grant_read(self.api_function)
        images_bucket.grant_read_write(self.api_function)

        # Grant Lambda access to Cognito for user management
        self.api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminUpdateUserAttributes",
                    "cognito-idp:ListUsers",
                ],
                resources=[user_pool.user_pool_arn],
            )
        )

        # API Gateway HTTP API
        self.http_api = apigwv2.HttpApi(
            self,
            "BlueMoxonApi",
            api_name="bluemoxon-api",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],  # Will be restricted
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.PATCH,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["*"],
                max_age=Duration.hours(1),
            ),
        )

        # Lambda integration
        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration",
            self.api_function,
        )

        # Route all requests to Lambda
        self.http_api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=lambda_integration,
        )

        # Output
        self.api_url = self.http_api.url
