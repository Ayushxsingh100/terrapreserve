variable "vpc_id" {
  description = "VPC ID where the security groups will be created"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}