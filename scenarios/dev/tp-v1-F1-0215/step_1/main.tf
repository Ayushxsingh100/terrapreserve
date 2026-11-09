resource "aws_security_group" "frontend_sg" {
  vpc_id = var.vpc_id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
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
  tags = {
    Name = "frontend-sg"
  }
}

resource "aws_security_group" "backend_sg" {
  vpc_id = var.vpc_id
  ingress {
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
  tags = {
    Name = "backend-sg"
  }
}

resource "aws_instance" "frontend" {
  count               = var.frontend_instance_count
  ami                 = var.ami_id
  instance_type       = var.instance_type
  subnet_id           = element(var.public_subnet_ids, count.index % length(var.public_subnet_ids))
  vpc_security_group_ids  = [aws_security_group.frontend_sg.id]

  tags = {
    Name = "frontend-${count.index + 1}"
  }
}

resource "aws_instance" "backend" {
  count               = var.backend_instance_count
  ami                 = var.ami_id
  instance_type       = var.instance_type
  subnet_id           = element(var.private_subnet_ids, count.index % length(var.private_subnet_ids))
  vpc_security_group_ids  = [aws_security_group.backend_sg.id]

  tags = {
    Name = "backend-${count.index + 1}"
  }
}
