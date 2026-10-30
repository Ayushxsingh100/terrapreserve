variable "vpc_id" {
  type = string
}

variable "vpc_cidr_block" {
  type = string
}

variable "project_name" {
  type = string
}

variable "subnets_ids" {
  type = list(string)
}

variable "engine_version" {
  type = string
}

variable "instance_class" {
  type = string
}

variable "db_name" {
  type = string
}

variable "username" {
  type      = string
  sensitive = true
}

variable "password" {
  type      = string
  sensitive = true
}

variable "availability_zone" {
  type = string
}

variable "publicly_accessible" {
  type = bool
}

variable "ca_cert_identifier" {
  type = string
}
