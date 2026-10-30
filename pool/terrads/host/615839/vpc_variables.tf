variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "vpc_public_subnet_cidr_1" {
  description = "CIDR block for the first public subnet"
  type        = string
}

variable "vpc_public_subnet_cidr_2" {
  description = "CIDR block for the second public subnet"
  type        = string
}

# variable "vpc_priv_sub_cidr" {
#   description = "CIDR block for the VPC"
#   type        = string
# }
