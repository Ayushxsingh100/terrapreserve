variable "cidr_block" {
  description = "CIDR block for VPC"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
}

variable "subnet_az_a" {
  description = "CIDR block for subnet in availability zone A"
  type        = string
}

variable "subnet_az_b" {
  description = "CIDR block for subnet in availability zone B"
  type        = string
}