# private: PostgreSQL port 5432 admitted from 10.0.0.0/16, in both rule forms.
resource "aws_security_group" "inline" {
  name = "inline"

  ingress {
    protocol    = "tcp"
    from_port   = 5432
    to_port     = 5432
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_security_group" "separate" {
  name = "separate"
}

resource "aws_security_group_rule" "pg" {
  type              = "ingress"
  security_group_id = aws_security_group.separate.id
  protocol          = "tcp"
  from_port         = 5432
  to_port           = 5432
  cidr_blocks       = ["10.0.0.0/16"]
}
