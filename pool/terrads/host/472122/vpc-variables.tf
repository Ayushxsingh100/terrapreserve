##############################################
## Network Single AZ Public Only - Variables #
##############################################


# VPC Variables
variable "vpc_cidr" {
  type        = string
  description = "CIDR for the VPC"
  default     = "10.100.0.0/16"
}

variable "vpc_name" {
  type        = string
  description = "Name of the VPC"
  default     = "vpc100"
}

# Subnet Variables
variable "public_subnet_cidr1" {
  type        = string
  description = "CIDR for the public subnet"
  default     = "10.100.11.0/24"
}

# Subnet Variables
variable "public_subnet_cidr2" {
  type        = string
  description = "CIDR for the public subnet"
  default     = "10.100.12.0/24"
}

# Subnet Variables
variable "private_subnet_cidr1" {
  type        = string
  description = "CIDR for the public subnet"
  default     = "10.100.21.0/24"
}

# Subnet Variables
variable "private_subnet_cidr2" {
  type        = string
  description = "CIDR for the public subnet"
  default     = "10.100.22.0/24"
}