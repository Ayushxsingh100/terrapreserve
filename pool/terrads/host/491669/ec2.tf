provider "aws" {
  region = "ap-south-1"  
}

//////////////////////////creation starts///

resource "aws_instance" "myec2" {
  ami           = "ami-0f5ee92e2d63afc18"   
  instance_type = "t2.nano"
  root_block_device {
    volume_size = 8  
    volume_type = "gp2"
  }
    tags = {
    Name = "self-cloud-server"
  }
}

resource "aws_security_group" "mysg" {
  name        = "my-security-group"
  description = "My security group"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Add any other necessary ingress rules for your use case

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "self-cloud-server-sg"
  }
}
