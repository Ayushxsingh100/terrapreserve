resource "aws_security_group" "bastion" {
  vpc_id = var.vpc_id
  name   = "bastion-sg"
  description = "SSH from admin"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  egress { 
    from_port = 0 
    to_port = 0 
    protocol = "-1" 
    cidr_blocks = ["0.0.0.0/0"] 
  }
  tags = merge(var.tags, { Name = "bastion-sg" })
}

resource "aws_security_group" "app" {
  vpc_id = var.vpc_id
  name   = "app-sg"
  description = "App accepts SSH from bastion only"

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress { 
        from_port = 0 
        to_port = 0 
        protocol = "-1" 
        cidr_blocks = ["0.0.0.0/0"] 
    }
  tags = merge(var.tags, { Name = "app-sg" })
}