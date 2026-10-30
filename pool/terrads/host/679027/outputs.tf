#=============================================================================
# Security Module - Outputs
#=============================================================================

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "sales_security_group_id" {
  description = "ID of the SalesTeam security group"
  value       = aws_security_group.sales.id
}

output "compliance_security_group_id" {
  description = "ID of the ComplianceTeam security group"
  value       = aws_security_group.compliance.id
}

output "dtransformation_security_group_id" {
  description = "ID of the DTransformationTeam security group"
  value       = aws_security_group.dtransformation.id
}

output "devops_security_group_id" {
  description = "ID of the DevOpsTeam security group"
  value       = aws_security_group.devops.id
}

output "redteam_security_group_id" {
  description = "ID of the RedTeam security group"
  value       = aws_security_group.redteam.id
}

output "administrative_security_group_id" {
  description = "ID of the AdministrativeTeam security group"
  value       = aws_security_group.administrative.id
}

output "all_security_group_ids" {
  description = "Map of all security group IDs"
  value = {
    alb             = aws_security_group.alb.id
    sales           = aws_security_group.sales.id
    compliance      = aws_security_group.compliance.id
    dtransformation = aws_security_group.dtransformation.id
    devops          = aws_security_group.devops.id
    redteam         = aws_security_group.redteam.id
    administrative  = aws_security_group.administrative.id
  }
}
