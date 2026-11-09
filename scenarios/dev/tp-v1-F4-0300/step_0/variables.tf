variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "subnet_count" {
  type        = number
  default     = 2
  description = "Number of public/private subnets"
}

variable "project" {
  type        = string
  description = "Project or system identifier"
}

variable "environment" {
  type        = string
  description = "Environment name (dev/staging/prod)"
}
