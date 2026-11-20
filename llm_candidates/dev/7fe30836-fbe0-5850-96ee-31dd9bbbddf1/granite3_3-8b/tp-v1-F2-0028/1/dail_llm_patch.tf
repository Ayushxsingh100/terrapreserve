resource "aws_security_group_rule" "acme_db_sg_from_app_ipv4" {
  type = "ingress"
  from_port   = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.acme_db_sg.id
  source_security_group_id = aws_security_group.acme_app_sg.id
  cidr_blocks = ["${aws_security_group.acme_app_sg.arn}"]
}

resource "aws_security_group_rule" "acme_db_sg_from_app_ipv6" {
  type = "ingress"
  from_port   = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.acme_db_sg.id
  source_security_group_id = aws_security_group.acme_app_sg.id
  cidr_blocks = ["::/0"]
}

resource "aws_security_group_rule" "acme_db_sg_restrict_public_ipv4" {
  type = "ingress"
  from_port   = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.acme_db_sg.id
  cidr_blocks = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "172.31.0.0/19",
    "192.0.0.0/24",
    "::/120"
  ]
}

resource "aws_security_group_rule" "acme_db_sg_restrict_public_ipv6" {
  type = "ingress"
  from_port   = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.acme_db_sg.id
  cidr_blocks = [
    "::/120"
  ]
}
