variable "public_subnet_name" {
  description = "Base name for public subnets"
  type        = string
}

variable "vpc_id" {
  description = "The VPC ID"
  type        = string
}

variable "public_cidr_blocks" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
}

variable "public_availability_zones" {
  description = "List of availability zones for public subnets"
  type        = list(string)
}


variable "env" {
  description = "The environment name"
  type        = string
}

variable "cluster_name" {
  description = "The name of the Kubernetes cluster"
  type        = string
}

variable "public_subnet_count" {
  description = "Number of public subnets"
  type        = number
}

variable "private_subnet_count" {
  description = "Number of private subnets"
  type        = number
}

variable "private_cidr_blocks" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)
}



variable "private_availability_zones" {
  description = "List of availability zones for private subnets"
  type        = list(string)
}

variable "private_subnet_name" {
  description = "Base name for private subnets"
  type        = string
}




