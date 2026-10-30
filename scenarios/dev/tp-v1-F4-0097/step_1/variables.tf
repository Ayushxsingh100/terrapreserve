variable "db_password" {
  description = "The RDS master password (passed at apply time; no default)."
  sensitive   = true
  type        = string

  validation {
    condition     = length(var.db_password) > 0
    error_message = "db_password must not be empty."
  }
}
