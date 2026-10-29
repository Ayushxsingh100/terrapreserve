variable "name" {
  description = "Name of the RDS instance"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "username" {
  description = "Master username"
  type        = string
}

variable "password" {
  description = "Master password"
  type        = string
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "13.4"
}

variable "instance_class" {
  description = "Instance type for the RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage size in GB"
  type        = number
  default     = 20
}

variable "subnet_ids" {
  description = "List of subnet IDs for the RDS instance"
  type        = list(string)
}

variable "create_security_group" {
  description = "Whether to create a security group for RDS"
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "VPC ID for the RDS security group"
  type        = string
}

variable "immediately" {
  description = "Apply change immediately"
  type        = bool
}

variable "allow_cidr_blocks" {
  description = "List of CIDR blocks to allow for RDS ingress"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Tags to assign to the resources"
  type        = map(string)
  default     = {}
}