variable "access_key" {}

variable "secret_key" {}

variable "region" {
  default = "us-east-1"
}

variable "aws_vpc_id" {}

variable "icmp_cidr" {
  default = "0.0.0.0/0"
}

variable "ssh_cidr" {
  default = "0.0.0.0/0"
}

variable "ssh_port" {
  default = "22"
}

variable "nomad_cidr" {
  default = "0.0.0.0/0"
}
