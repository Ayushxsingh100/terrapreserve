resource "aws_security_group" "public_sg" {
  name        = "${var.project_name}-public-sg"
  description = "Security Group for Public EC2"
  vpc_id      = var.vpc_id

  ingress {
    description      = "Allow SSH from user IP"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = [var.my_ip]
  }

  egress {
    description      = "Allow all outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-public-sg"
  }
}

resource "aws_security_group" "private_sg" {
  name        = "${var.project_name}-private-sg"
  description = "Security Group for Private EC2"
  vpc_id      = var.vpc_id

  # Allow SSH from Public SG
  ingress {
    description            = "Allow SSH from Public EC2"
    from_port              = 22
    to_port                = 22
    protocol               = "tcp"
    security_groups        = [aws_security_group.public_sg.id]
  }

  egress {
    description      = "Allow all outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-private-sg"
  }
}
