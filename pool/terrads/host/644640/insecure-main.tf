# Insecure example: open security group / security rule
provider "aws" {
  region = "us-east-1"
}

resource "aws_security_group" "insecure" {
  name = "insecure-sg"
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # <-- open to the world, insecure
  }
}
