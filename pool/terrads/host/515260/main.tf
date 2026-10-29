# Terraform AWS EC2 Instance Example

# Configure the AWS provider
provider "aws" {
  region = "us-east-1" # Specify your desired AWS region
}

# Define variables for customization
variable "instance_name" {
  description = "The name for the EC2 instance"
  type        = string
  default     = "my-instance"
}

variable "instance_type" {
  description = "The instance type for the EC2 instance"
  type        = string
  default     = "t2.micro"
}

# Create a security group
resource "aws_security_group" "example_sg" {
  name        = "example-sg"
  description = "Example security group for EC2 instance"

  # Define ingress rules to allow SSH and HTTP traffic
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow SSH from anywhere
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow HTTP from anywhere
  }
}

# Create an EC2 instance
resource "aws_instance" "example_instance" {
  ami           = "ami-0c55b159cbfafe1f0" # Specify your desired AMI
  instance_type = var.instance_type
  key_name      = "my-key" # Specify your SSH key pair

  # Attach the security group to the instance
  vpc_security_group_ids = [aws_security_group.example_sg.id]

  tags = {
    Name = var.instance_name
  }
}

# Output the public IP address of the created instance
output "public_ip" {
  value       = aws_instance.example_instance.public_ip
  description = "Public IP address of the EC2 instance"
}

# Output the instance ID
output "instance_id" {
  value       = aws_instance.example_instance.id
  description = "ID of the EC2 instance"
}
