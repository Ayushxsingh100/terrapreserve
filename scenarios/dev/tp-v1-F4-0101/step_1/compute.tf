resource "aws_security_group_rule" "service_access_ssh_public" {
  cidr_blocks       = ["10.0.0.0/8"]
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.service_access.id
  to_port           = 22
  type              = "ingress"
}

resource "aws_security_group_rule" "service_access_egress_db" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.service_access.id
  source_security_group_id = aws_security_group.storage_access.id
  to_port                  = 5432
  type                     = "egress"
}

resource "aws_security_group" "service_access" {
  description = "Application security group for tpl-26"
  name        = "service_access-tpl-26"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_security_group" "service_access_extra" {
  description = "Secondary application security group for tpl-26"
  name        = "service_access_extra-tpl-26"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_instance" "service_node" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.service.id
  vpc_security_group_ids = [aws_security_group.service_access.id, aws_security_group.service_access_extra.id]
}
