variable "vpc_id" {
  description = "VPC ID where ECS tasks will run"
  type        = string
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
  default     = "steampipe-aws-monitor"
}


