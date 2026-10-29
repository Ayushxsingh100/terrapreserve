provider "aws" {
  region = "us-east-1" # Change this to your preferred region
}

resource "aws_security_group" "ssh_access" {
  name        = "ssh_access"
  description = "Allow SSH access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "example" {
  ami           = "ami-005fc0f236362e99f" #ununtu , for awsami, use ami-08982f1c5bf93d976
  instance_type = "t2.micro"
  key_name      = "vockey"
  vpc_security_group_ids = [aws_security_group.ssh_access.id]

  tags = {
    Name = "OpenTofu-Instance"
  }
}