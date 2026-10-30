variable "aws_region" {
  description = "The AWS region to deploy resources in"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "The EC2 instance type"
  default     = "t2.micro"
}

variable "key_name" {
  description = "The name of the key pair to use for the instance"
  default     = "my-key-pair"
}

variable "ami_id" {
  description = "The Amazon Machine Image (AMI) ID to use for the instance"
  default     = "ami-0c02fb55956c7d316" # Amazon Linux 2 AMI in us-east-1
}

variable "security_group_name" {
  description = "The name of the security group"
  default     = "my-ec2-security-group"
}
