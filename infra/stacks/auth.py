"""Auth Stack - Cognito User Pool with MFA."""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_cognito as cognito,
)
from constructs import Construct


class AuthStack(Stack):
    """Creates Cognito User Pool with required MFA."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # User Pool
        self.user_pool = cognito.UserPool(
            self,
            "BlueMoxonUserPool",
            user_pool_name="bluemoxon-users",
            self_sign_up_enabled=False,  # Admin invite only
            sign_in_aliases=cognito.SignInAliases(
                email=True,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
            ),
            custom_attributes={
                "role": cognito.StringAttribute(
                    min_len=1,
                    max_len=20,
                    mutable=True,
                ),
            },
            mfa=cognito.Mfa.OPTIONAL,  # App enforces MFA setup on first login
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=False,
                otp=True,  # TOTP only
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
                temp_password_validity=Duration.days(7),
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # App Client for Frontend
        self.app_client = self.user_pool.add_client(
            "BlueMoxonAppClient",
            user_pool_client_name="bluemoxon-web",
            auth_flows=cognito.AuthFlow(
                user_srp=True,
            ),
            generate_secret=False,  # Public client
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )

        # Domain for hosted UI (optional)
        self.user_pool_domain = self.user_pool.add_domain(
            "BlueMoxonDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="bluemoxon",
            ),
        )
