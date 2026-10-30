variable "aws_region" {
  type = string
  default = "us-east-1"
}

variable "rds_instance_class" {
  type = string
  default = "db.t4g.micro"
}

variable "rds_username" {
  type = string
  default = "postgres"
}

variable "rds_password" {
  type = string
  sensitive = true
}

variable "rds_database_name" {
  type = string
  default = "master"
}