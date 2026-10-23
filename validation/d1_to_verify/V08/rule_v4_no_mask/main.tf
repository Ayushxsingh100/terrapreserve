provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_security_group" "g" {
  name   = "g"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group_rule" "r" {
  type              = "ingress"
  security_group_id = aws_security_group.g.id
  protocol          = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.1"]
}
