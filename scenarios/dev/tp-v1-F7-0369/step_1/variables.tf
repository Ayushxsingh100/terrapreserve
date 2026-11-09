# ---------------------------------------------------------------------------------------------------------------------
# REQUIRED PARAMETERS
# You must provide a value for each of these parameters.
# ---------------------------------------------------------------------------------------------------------------------
variable "region" {
  description = "The AWS region things are created in"
}

variable "aws_account_id" {
  description = "The AWS Account ID to deploy the resources to"
  type        = string
}

variable "env" {
  description = "environment"
}

variable "default_tags" {
  type = map(any)
}

variable "name" {
  type = string
}

variable "cidr_blocks" {
  description = "the first two octets of the vpc (e.g. 10.10)"
  type        = string
}

variable "private_subnet_cidr_blocks" {
  type        = list(string)
  description = "CIDR ranges for the private subnets"
}



# ---------------------------------------------------------------------------------------------------------------------
# OPTIONAL PARAMETERS
# These parameters have reasonable defaults.
# ---------------------------------------------------------------------------------------------------------------------

variable "region-letters" {
  type        = list(string)
  description = "region letter suffixes"
  default     = ["a", "b", "c"]
}
variable "tags" {
  type    = map(any)
  default = {}
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames for this VPC: Default = False"
  type        = bool
  default     = false
}
