# Required provider
provider "aws" {
  region = "us-east-1" # Change to your desired region
}

# Security Group
resource "aws_security_group" "ec2_security_group" {
  name_prefix = "ec2-sg-"
  description = "Security group for EC2 instance"

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EC2 Instance
resource "aws_instance" "example" {
  ami           = var.ami
  instance_type = var.instance_type  
  key_name      = var.key_name

  # Security group
  vpc_security_group_ids = [aws_security_group.ec2_security_group.id]

  # Enable public IP
  associate_public_ip_address = true

  # Encrypted EBS volume
  root_block_device {
    volume_size           = var.volume_size             # Change to your desired volume size (in GiB)
    volume_type           = var.volume_size          # Change to your desired volume type
    encrypted             = true           # Enable encryption
    delete_on_termination = true       # Optional: delete volume when instance terminates
  }

  tags = {
    Name = "Terraform-EC2-Instance"
  }
}
