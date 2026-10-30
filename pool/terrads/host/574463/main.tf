variable "vpc_id" {}
variable "DOCKER_PORT" {}
variable "vpc_cidr" {}

output "security_group_id" {
  value = aws_security_group.web_server_sg.id
}


resource "aws_security_group" "web_server_sg" {
  name        = "aws-web-server-security-group"
  description = "Security group for web servers"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = var.DOCKER_PORT
    to_port     = var.DOCKER_PORT
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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
