provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "smoke" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_security_group" "smoke" {
  name   = "terrapreserve-smoke"
  vpc_id = aws_vpc.smoke.id
}
