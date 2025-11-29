"""DNS Stack - Route 53 and ACM certificates."""

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
)
from constructs import Construct


class DnsStack(Stack):
    """Creates Route 53 hosted zone and DNS records."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        domain_name: str,
        frontend_distribution: cloudfront.Distribution,
        api_distribution: cloudfront.Distribution | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Hosted Zone (assumes domain is registered in Route 53 or NS delegated)
        self.hosted_zone = route53.HostedZone(
            self,
            "HostedZone",
            zone_name=domain_name,
        )

        # ACM Certificate (must be in us-east-1 for CloudFront)
        self.certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=domain_name,
            subject_alternative_names=[f"*.{domain_name}"],
            validation=acm.CertificateValidation.from_dns(self.hosted_zone),
        )

        # A record for frontend (apex domain)
        route53.ARecord(
            self,
            "FrontendARecord",
            zone=self.hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(frontend_distribution)
            ),
        )

        # AAAA record for frontend (IPv6)
        route53.AaaaRecord(
            self,
            "FrontendAaaaRecord",
            zone=self.hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(frontend_distribution)
            ),
        )

        # www subdomain redirect (optional)
        route53.ARecord(
            self,
            "WwwARecord",
            zone=self.hosted_zone,
            record_name="www",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(frontend_distribution)
            ),
        )

        # Outputs
        CfnOutput(
            self,
            "DomainName",
            value=domain_name,
            description="Domain name",
        )

        CfnOutput(
            self,
            "NameServers",
            value=", ".join(self.hosted_zone.hosted_zone_name_servers or []),
            description="Name servers (update domain registrar if external)",
        )

        CfnOutput(
            self,
            "CertificateArn",
            value=self.certificate.certificate_arn,
            description="ACM certificate ARN",
        )
