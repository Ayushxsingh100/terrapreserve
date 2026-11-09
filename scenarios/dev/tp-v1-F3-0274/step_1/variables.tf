variable "resource_prefix" {
  type        = string
  description = "Prefix for resource names"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the RDS instance"
}

variable "db_password" {
  type        = string
  description = "Password for the RDS PostgreSQL database"
  sensitive   = true
}

variable "instance_class" {
  type        = string
  description = "Instance class for the RDS PostgreSQL database"
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage for the RDS instance (in GB)"
}

variable "multi_az" {
  type        = bool
  description = "Enable Multi-AZ for RDS (high availability)"
}