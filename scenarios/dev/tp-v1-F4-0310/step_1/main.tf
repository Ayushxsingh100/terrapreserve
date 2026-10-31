# security group
resource "aws_security_group" "btc" {
  name        = "btc_alert_api_sg"
  description = "Allow TLS BTC API to function"
  vpc_id      = var.vpc_id

  ingress {
    description      = "SSH from all"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Port 3000 from ELB"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"

    security_groups = [aws_security_group.btc_lb.id]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "btc_alert_api_sg"
  }
}

resource "aws_security_group" "btc_lb" {
  name        = "btc-alert-api"
  description = "Allow API traffic from UI to API"
  vpc_id      = var.vpc_id

  ingress {
    description      = "SSL from Cloudfront"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "btc_alert_api_lb_sg"
  }
}