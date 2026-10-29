variable "project_name" {
  description = "Project names for the database"
  type        = string
  default     = "petclinic-project"
}

# Database engine and version
variable "db_engine" {
  description = "Database engine (postgres, mysql, etc.)"
  type        = string
  default     = "mysql"
}

variable "db_engine_version" {
  description = "Version of the database engine"
  type        = string
  default     = "8.0.43"
}

# Instance configuration
variable "db_instance_class" {
  description = "Instance type for RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

# Database name and credentials
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "petclinic"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "appuser"
}

variable "db_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
}

# Networking
variable "db_port" {
  description = "Port number for the database"
  type        = number
  default     = 3306
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the DB"
  type        = list(string)
  default     = ["10.10.11.0/24", "10.10.12.0/24"] # private app subnets
}

variable "private_db_subnet_ids" {
  description = "List of subnet IDs for DB subnet group"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "app_security_group_id" {
  description = "Security group ID of application instances allowed to access the DB"
  type        = string
  default     = null
}

variable "admin_cidr" {
  description = "Admin CIDR for temporary DB access during setup"
  type        = string
  default     = null
}

variable "tags" {
  description = "rds Tags to apply to resources"
  type        = map(string)
  default = {
    Name = "rds"
  }
}
