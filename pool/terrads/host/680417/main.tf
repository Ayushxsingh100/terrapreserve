resource "aws_security_group" "app_sg" {
  name = "terraform-app-sg"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App Port"
    from_port   = 8080
    to_port     = 8080
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

resource "aws_instance" "app_server" {
  ami           = "ami-0a628e1e89aaedf80" # Amazon Linux 2023 (Frankfurt)
  instance_type = var.instance_type
  key_name      = "springboot-key"

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  tags = {
    Name = "Terraform-App-Server"
  }
}
