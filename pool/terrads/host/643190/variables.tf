# Variables to define module vpc
# For user to populate values in the ./main.tf file
# type: to set accepted data type

variable "dev_cicd_vpc_cidr" {
  type = string
}

variable "dev_cicd_vpc_public_subnet_cidr" {
}

variable "ssh_client_ip" {
  type = string
}