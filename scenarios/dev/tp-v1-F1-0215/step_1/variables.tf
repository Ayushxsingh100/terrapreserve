variable "vpc_id" {
  description = "The VPC ID."
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs."
  type        = list(string)
}

variable "ami_id" {
  description = "The AMI ID to use for the instances."
  type        = string
}

variable "instance_type" {
  description = "The instance type."
  type        = string
}

variable "frontend_instance_count" {
  description = "Number of frontend instances."
  type        = number
}

variable "backend_instance_count" {
  description = "Number of backend instances."
  type        = number
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks."
  type        = list(string)
}
