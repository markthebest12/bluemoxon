# =============================================================================
# DNS Module Outputs
# =============================================================================

output "zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.this.zone_id
}

output "zone_name_servers" {
  description = "Route53 hosted zone name servers"
  value       = aws_route53_zone.this.name_servers
}

output "zone_arn" {
  description = "Route53 hosted zone ARN"
  value       = aws_route53_zone.this.arn
}
