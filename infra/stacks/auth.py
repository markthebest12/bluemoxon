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

        # Custom invitation email template
        invitation_email_body = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">BlueMoxon</h1>
        <p style="color: #dbeafe; margin: 10px 0 0 0; font-size: 14px;">Book Collection Management</p>
    </div>
    <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1e293b; margin: 0 0 20px 0; font-size: 20px;">Welcome to BlueMoxon!</h2>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 20px 0;">
            You've been invited to join BlueMoxon. Use the credentials below to sign in:
        </p>
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; color: #64748b; font-size: 14px;"><strong>Username:</strong></p>
            <p style="margin: 0 0 20px 0; color: #1e293b; font-size: 16px; font-family: monospace; background: #f1f5f9; padding: 10px; border-radius: 4px;">{username}</p>
            <p style="margin: 0 0 10px 0; color: #64748b; font-size: 14px;"><strong>Temporary Password:</strong></p>
            <p style="margin: 0; color: #1e293b; font-size: 16px; font-family: monospace; background: #f1f5f9; padding: 10px; border-radius: 4px;">{####}</p>
        </div>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 20px 0;">
            You'll be asked to create a new password when you first sign in.
        </p>
        <div style="text-align: center; margin-top: 30px;">
            <a href="https://app.bluemoxon.com" style="background: #2563eb; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">Sign In to BlueMoxon</a>
        </div>
        <p style="color: #94a3b8; font-size: 12px; margin: 30px 0 0 0; text-align: center;">
            This invitation expires in 7 days. If you didn't expect this invitation, please ignore this email.
        </p>
    </div>
</div>
"""

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
            user_invitation=cognito.UserInvitationConfig(
                email_subject="Welcome to BlueMoxon - Your Account is Ready",
                email_body=invitation_email_body,
            ),
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
