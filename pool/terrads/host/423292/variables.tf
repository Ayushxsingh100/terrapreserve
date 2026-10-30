variable "ami_id" {
  default = "ami-0cf6160d953e96b60"
  description = "This is the id for the AMI (image)"
  type = string
}
variable "instance_type" {
  default = "t2.micro"
}
variable "tags" {
  default = {
      Name = "practica-uno"
      Environment = "Dev"
  }
  description = "Tags for EC2 instance"
}
variable "sg_name" {
  
}
variable "ingress_rules" {
  
}