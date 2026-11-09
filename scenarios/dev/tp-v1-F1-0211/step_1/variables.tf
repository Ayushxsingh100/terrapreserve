variable "aws_region" {
  type        = string
  description = "Aws region"
  default     = "us-east-1"
}

variable "profile" {
  type        = string
  description = "Aws credentials profile"
  default     = "tf001"
}

variable "instance_ami" {
  type        = string
  description = "AWS EC2 Instance AMI"
  default     = "ami-04b70fa74e45c3917"
}

variable "instance_type" {
  type        = string
  description = "AWS EC2 Instance type"
  default     = "t2.micro"
}

variable "bucket_name" {
  type        = string
  description = "AWS S3 bucket name"
  default     = "daniloanobre-remote-state"

}

variable "instance_tags" {
  type        = map(string)
  description = ""
  default = {
    Name    = "Ubuntu"
    Project = "Curso AWS com Terraform"
  }
}