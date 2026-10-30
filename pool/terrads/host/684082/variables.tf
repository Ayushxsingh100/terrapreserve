variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "eks_security_group_id" { type = string }

variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "multi_az" { type = bool }

# For dev: keep simple; for prod: use Secrets Manager + external-secrets
variable "username" { 
type = string
default = "postgres"
}

variable "password" {
  type      = string
  sensitive = true
  default   = "CHANGE_ME_DEV_ONLY"
}
