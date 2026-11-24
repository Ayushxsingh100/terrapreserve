# subnet/variables.tf

variable "cidr" {
  description = "The CIDR block of the VPC"
  type        = string
}

variable "subnet_bits" {
  description = "The number of bits for subnet"
  type        = number
}

variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
}

variable "cluster_prefix" {
  description = "Prefix for the cluster"
  type        = string
}

variable "subnet_type" {
  description = "Type of subnet"
  type        = string
}

variable "offset" {
  type = number
}
