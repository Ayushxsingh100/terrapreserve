# security-groups/main.tf

resource "aws_security_group" "vpc_1_sg" {
    name = "service 1 security group"
    description = "enable http/https access to vpc lattice service network"
    vpc_id = var.vpc_1_vpc_id

  egress {
    description = "outbound http access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "outbound https access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "vpc_2_sg" {
    name = "service 2 security group"
    description = "enable http/https access to vpc lattice service network"
    vpc_id = var.vpc_2_vpc_id

  ingress {
    description     = "https access"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
  }

  egress {
    description = "outbound http access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "outbound https access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

