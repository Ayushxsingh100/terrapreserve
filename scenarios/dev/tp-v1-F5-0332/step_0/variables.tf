// Providers
variable "aws_region" {}

// VPC
variable "vpc_id" {
  type        = string
  description = "ID of a existing VPC" 
}

// Security groups
variable "sgData" {
  type        = list
  description = "List of rules which required for creating security group(s)"
}