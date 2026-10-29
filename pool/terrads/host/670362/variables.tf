variable "project_name" {
  type     = string
  nullable = false
}

variable "cidr_block" {
  type     = string
  nullable = false
}

variable "public_cidr_block" {
  type     = list(string)
  nullable = false
}

variable "private_cidr_block" {
  type     = list(string)
  nullable = false
}
