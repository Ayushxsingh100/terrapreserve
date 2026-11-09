
variable "region" {
  type = string
  description = "AWS region"
  default = "eu-west-1"
}

variable "target_vpc" {
  type = string
  description = "The target vpc"
}

variable "cluster_name" {
  type = string
  description = "The cluster name"
}

variable "subnet_cidr" {
  type = string
  description = "Subnet CIDR"
}

variable "tfstate_name" {
  type = string
  description = "TFState filename"
}