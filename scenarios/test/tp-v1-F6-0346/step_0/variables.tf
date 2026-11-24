# ---------------------------------------------------------------------------------------------------------------------
# REQUIRED PARAMETERS
# You must provide a value for each of these parameters.
# ---------------------------------------------------------------------------------------------------------------------

variable "db_name" {
  description = "The name to use for the database"
  type        = string
}
variable "db_username" {
  description = "The username for the database"
  type        = string
}
variable "db_password" {
  description = "The password for the database"
  type        = string
}
variable "db_port" {
  description = "The port number used by the database"
  type        = number
}
variable "engine" {
  description = "The engine for the database"
  type        = string
}
variable "identifier_prefix" {
  description = "The actual name to use for the database"
  type        = string
}
variable "instance_class" {
  description = "The instance class for the database"
  type        = string
}
variable "storage" {
  description = "The storage size for the database"
  type        = string
}
variable "security_group_id" {
  description = "The security group id to associate with the database"
  type        = string
}
variable "vpc_id" {
  description = "The VPC ID"
  type        = string
}
variable "private_subnet_ids" {
  description = "A private subnet ID to deploy the DB instance in"
  type        = list(string)
}

# ---------------------------------------------------------------------------------------------------------------------
# OPTIONAL PARAMETERS
# These parameters have reasonable defaults.
# ---------------------------------------------------------------------------------------------------------------------

variable "availability_zone" {
  description = "The availability zone to deploy instances in"
  type        = string
  default     = null
}