provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "app_instance" {
  ami           = "ami-071226ecf16aa7d96"  # Update with the correct AMI ID
  instance_type = "t2.micro"

  tags = {
    Name = "ContainerAppInstance"
  }
}

resource "aws_security_group" "app_sg" {
  name        = "app_sg"
  description = "Allow inbound traffic on port 5000"
  
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "instance_ip" {
  value = aws_instance.app_instance.public_ip
}
