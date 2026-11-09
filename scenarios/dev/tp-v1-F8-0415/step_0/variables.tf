variable "region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "subnet_app_cidr" {
  description = "CIDR block for the application subnet"
  default     = "10.0.1.0/24"
}

variable "app_ami" {
  description = "AMI for the application server"
}

variable "instance_type" {
  description = "Instance type for the application server"
  default     = "t2.micro"
}
