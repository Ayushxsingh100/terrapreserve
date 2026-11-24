variable "vpc_cidr" {
  type        = string
  description = "IPv4 CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "number_of_availability_zones" {
  type        = number
  description = "Number of availabilitiy zones to use"
  default     = 2
}

variable "enable_public_subnets" {
  type        = bool
  description = "Whether to create public subnets"
  default     = false
}

variable "enable_nat_subnets" {
  type        = bool
  description = "Whether to create nat subnets"
  default     = false
}

variable "enable_private_subnets" {
  type        = bool
  description = "Whether to create private subnets"
  default     = false
}
