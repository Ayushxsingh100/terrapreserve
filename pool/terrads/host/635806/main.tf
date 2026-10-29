#================================================#
#-------------------SG-Module--------------------#
#================================================#

#ALB Security Group
#allow inbound for 80/443 from anywhere

resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  vpc_id      = var.vpc_id
  description = "Allows inbound HTTP/HTTPS"

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

  tags = merge({ Name = "alb-sg" }, var.tags)
}

#App Security Group 
#allow inbound only from alb

resource "aws_security_group" "app_sg" {
  name        = "app-sg"
  vpc_id      = var.vpc_id
  description = "Allows inbound traffic from ALB"

  ingress {
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge({ Name = "app-sg" }, var.tags)
}

#DB Security Group
#allow inbound only from app servers

resource "aws_security_group" "db_sg" {
  name        = "db-sg"
  vpc_id      = var.vpc_id
  description = "Allows DB inbound only from app SG"

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge({Name = "db-sg"}, var.tags)
}
