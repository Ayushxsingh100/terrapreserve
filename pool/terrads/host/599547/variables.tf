variable "aws_region" {
  description = "The AWS region to deploy in"
  type        = string
  default     = "ap-south-1"
}

variable "ami_value" {
  description = "The AMI ID to use for the instance"
  type        = string
  default     = "ami-00bb6a80f01f03502"
}

variable "instance_type_value" {
  description = "The instance type to use"
  type        = string
  default     = "t2.micro"
}

variable "vpc_id" {
  description = "The VPC ID to launch the instance in"
  type        = string
  default     = "vpc-0d8b512e76c2b02d7"
}

variable "subnet_id_value" {
  description = "The subnet ID to launch the instance in"
  type        = string
  default     = "subnet-0194c32a03d44fdbd"
}