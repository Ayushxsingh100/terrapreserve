# modules/security_groups/variables.tf

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where security groups will be created"
  type        = string
}

variable "client_vpn_cidr" {
  description = "CIDR block allocated to Client VPN clients"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "value of CIDR blocks for private subnets"
  type        = list(string)
}

variable "isolated_subnet_cidrs" {
  description = "List of CIDR blocks for isolated subnets (for RDS)"
  type        = list(string)
}

variable "ec2_app_port" {
  description = "Port the application on EC2 instances listens on"
  type        = number
}

variable "ec2_app_port_health" {
  description = "Port the application on EC2 instances listens on for health check"
  type        = number
}