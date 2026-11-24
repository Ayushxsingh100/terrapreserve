# AWS
#variable "aws_access_key" {}
#variable "aws_secret_key" {}
variable "subnet_id" {}
variable "vpc_id" {}
variable "region" { default = "eu-central-1" }
variable "instance_size" { default = "t2.large" }
variable "instance_name" { default = "aviatrix-controller" }