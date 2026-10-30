provider "aws" {
  region = "us-east-1"
}

variable "instance_type" {
  description = "This is just instace type "
  type        = string
  default     = "t2.micro"
}

variable "ami" {
  description = "The value of ami of ubuntu"
  type        = string
  default     = "ami-084568db4383264d4"
}