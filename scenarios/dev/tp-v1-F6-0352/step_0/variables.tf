variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "backend_security_group_id" {
  description = "Backend security group ID for RDS access"
  type        = string
}