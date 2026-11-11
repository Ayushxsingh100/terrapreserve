variable "db_password" {
  description = "The RDS master password (passed at apply time; no default)."
  sensitive   = true
  type        = string

  validation {
    condition     = length(var.db_password) > 0
    error_message = "db_password must not be empty."
  }
}

variable "app_ami" {
  default     = "ami-0d5eff06f840b45e9"
  description = "AMI of the application instance."
  type        = string
}

variable "app_instance_type" {
  default     = "t3.small"
  description = "Instance type of the application instance."
  type        = string
}

variable "db_instance_class" {
  default     = "db.t3.micro"
  description = "Instance class of the database."
  type        = string
}
