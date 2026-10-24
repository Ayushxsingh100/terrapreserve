# public: PostgreSQL port 5432 admitted from 0.0.0.0/0, in both rule forms.
resource "aws_security_group" "inline" {
  name = "inline"

  ingress {
    protocol    = "tcp"
    from_port   = 5432
    to_port     = 5432
    cidr_blocks = ["0.0.0.0/0"]
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
  cidr_blocks       = ["0.0.0.0/0"]
}
