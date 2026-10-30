
variable "region" {
  default = "us-east-1"
}

variable "ami" {
  default = "ami-0e54eba7c51c234f6"
}

variable "instance_type" {
  default = "t2.micro"
}

variable "db_password" {
  type      = string
  sensitive = true
}
