resource "aws_security_group" "main" {
  vpc_id      = var.vpc_id
  name        = "${var.environment}-security-group"
  description = "Allow inbound traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
  }

  tags = {
    Name = "${var.environment}-sg"
  }
}
