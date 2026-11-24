variable "region" {
  type        = string
  description = "The region where the VPC will be deployed"
  default     = "eu-west-2"
}

variable "vpc_cidr" {
  type        = string
  description = "Classless Inter-Domain Routing block for the VPC"
  default     = "192.168.0.0/16"
}

variable "tag" {
  type        = string
  description = "The name of the tag"
  default     = "kiril.krastev@hashicorp.com"
}

variable "public_subnet_1" {
  type        = string
  description = "cidr routing block for public subnet"
  default     = "192.168.0.0/20"
}

variable "public_subnet_2" {
  type        = string
  description = "cidr routing block for public subnet"
  default     = "192.168.16.0/20"
}

variable "public_subnet_3" {
  type        = string
  description = "cidr routing block for public subnet"
  default     = "192.168.32.0/20"
}


variable "private_subnet_1" {
  type        = string
  description = "cidr routing block for private subnet"
  default     = "192.168.48.0/20"
}

variable "private_subnet_2" {
  type        = string
  description = "cidr routing block for private subnet"
  default     = "192.168.64.0/20"
}

variable "private_subnet_3" {
  type        = string
  description = "cidr routing block for private subnet"
  default     = "192.168.80.0/20"
}