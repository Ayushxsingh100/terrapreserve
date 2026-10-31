//Variabls for EC2 Instance
variable "ip" {
  default = "67.173.153.202/32"
}

variable "ami" {
  default = "ami-07ebfd5b3428b6f4d"
}

variable "instancetype" {
  default = "t2.micro"
}

variable "istest" {
  default = "false"
  type    = bool
}

variable "instancecount" {
  type    = number
  default = 1
}

//Variabls for Security Group
variable "sg_name" {
  default = "mysg"
}

variable "sg_vpc_id" {
  default = "vpc-e9532f90"
}

variable "sg_description" {
  default = "this is my sg"
}
