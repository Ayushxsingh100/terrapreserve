variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "subnet_count" {
  description = "Number of subnets to create"
  default     = 2
}

variable "name_prefix" {
  description = "Prefix to use for resource names"
  default     = "ecs-ecr-demo"
}