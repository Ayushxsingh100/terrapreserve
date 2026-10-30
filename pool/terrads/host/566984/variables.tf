variable "region" {
  default = "us-east-2"
}

variable "name_security_group" {
  default = "wp-security-group"
}

variable "ami_aws_instance" {
  default = "ami-09040d770ffe2224f"
}

variable "type_aws_instance" {
  default = "t2.micro"
}

variable "key_aws_instance" {
  default = "wp-key"
}