variable "vpc_id" {
  type = string
  description = "The ID of the VPC"
  default = "vpc-c2cdd4a5"
}

variable "sg_name" {
  description = "Name of the security group"
}