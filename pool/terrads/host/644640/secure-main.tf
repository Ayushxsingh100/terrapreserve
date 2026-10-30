# Secure example: restricted security group
provider "aws" {
  region = "us-east-1"
}

resource "aws_security_group" "secure" {
  name = "secure-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["203.0.113.0/24"]  # <-- restricted CIDR example
  }
}
