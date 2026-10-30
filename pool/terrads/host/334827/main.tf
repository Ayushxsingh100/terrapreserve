provider "aws" {
  region                  = "us-east-2"
  version                 = "~> 2.0"
  shared_credentials_file = "/home/marzo/.aws/credentials"
  profile                 = "terraform_teste"
}

resource "aws_vpc" "vpc_core" {
  cidr_block = "10.1.1.0/24"

  tags = {
    Name = "first_terraform"
  }
}

resource "aws_subnet" "dmz_t_a" {
  vpc_id     = "${aws_vpc.vpc_core.id}"
  cidr_block = "10.1.1.0/24"

  tags = {
    Name = "dmz_t_a"
  }
}
