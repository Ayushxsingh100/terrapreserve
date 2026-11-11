resource "aws_security_group_rule" "web_secgroup_ssh_public" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.web_secgroup.id
  to_port           = 22
  type              = "ingress"
}

resource "aws_security_group_rule" "web_secgroup_egress_db" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web_secgroup.id
  source_security_group_id = aws_security_group.data_secgroup.id
  to_port                  = 5432
  type                     = "egress"
}

resource "aws_security_group" "web_secgroup" {
  description = "Application security group for tpl-19"
  name        = "web_secgroup-tpl-19"
  vpc_id      = aws_vpc.network.id
}

resource "aws_security_group" "web_secgroup_ops" {
  description = "Operations security group for tpl-19, attached to nothing"
  name        = "web_secgroup_ops-tpl-19"
  vpc_id      = aws_vpc.network.id

  ingress {
    cidr_blocks = ["10.107.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "web_instance" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.small"
  subnet_id              = aws_subnet.web_tier.id
  vpc_security_group_ids = [aws_security_group.web_secgroup.id]
}
