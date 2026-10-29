#=============================================================================
# Security Module - Variables
#=============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks allowed for admin access (SSH, RDP)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
