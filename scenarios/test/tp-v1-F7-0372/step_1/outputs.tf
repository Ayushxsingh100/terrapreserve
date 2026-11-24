# ===============================
# AWS Networking Module Outputs
# ===============================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "internet_gateway_id" {
  description = "ID of the internet gateway"
  value       = aws_internet_gateway.main.id
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = var.tp_ds_aws_caller_identity_current.account_id
}

output "aws_caller_arn" {
  description = "AWS Caller ARN"
  value       = var.tp_ds_aws_caller_identity_current.arn
}
