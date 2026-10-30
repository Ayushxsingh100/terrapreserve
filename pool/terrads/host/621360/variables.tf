variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_1_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
}

variable "az_1" {
  description = "Availability zone"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}
