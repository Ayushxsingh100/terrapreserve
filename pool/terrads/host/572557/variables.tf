
# Name of the VPC
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = "sandbox_aws_vpc"
}

# CIDR block for the VPC
variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# CIDR blocks for the public subnets
variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for the public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

# CIDR blocks for the private subnets
variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for the private subnets"
  type        = list(string)
  default     = ["10.0.2.0/24"]
}

# Availability Zones
variable "availability_zones" {
  description = "List of Availability Zones to use"
  type        = list(string)
  default     = ["eu-west-2a"]
}