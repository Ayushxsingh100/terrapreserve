resource "aws_security_group" "prod_app_sg" {
  description = "Application security group for tpl-33"
  name        = "prod_app_sg-tpl-33"
  vpc_id      = aws_vpc.prod_vpc.id

  egress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.prod_db_sg.id]
    to_port         = 5432
  }
}

resource "aws_instance" "prod_app_server" {
  ami                    = local.app_ami
  instance_type          = local.app_instance_type
  subnet_id              = aws_subnet.prod_app_subnet.id
  vpc_security_group_ids = [aws_security_group.prod_app_sg.id]
}

resource "aws_security_group" "prod_db_sg_hub" {
  description = "Shared client security group"
  name        = "prod_db_sg-tpl-33-hub"
  vpc_id      = aws_vpc.prod_vpc.id
}
