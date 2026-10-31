resource "aws_vpc" "environment-ex-one" {
cidr_block = "10.0.0.0/16"
enable_dns_hostnames = true
enable_dns_support = true
tags = {
  Name = "terraform-aws-vpc-ex-one"
  }
}

resource "aws_subnet" "subnet1" {
cidr_block = "${cidrsubnet(aws_vpc.environment-ex-one.cidr_block, 3, 2)}"
vpc_id = "${aws_vpc.environment-ex-one.id}"
availability_zone = "us-east-1a"
}

resource "aws_subnet" "subnet2" {
cidr_block = "${cidrsubnet(aws_vpc.environment-ex-one.cidr_block, 2, 2)}"
vpc_id = "${aws_vpc.environment-ex-one.id}"
availability_zone = "us-east-1b"
}

resource "aws_security_group" "aws_sg1" {
vpc_id = "${aws_vpc.environment-ex-one.id}"
ingress {
cidr_blocks = [
  "${aws_vpc.environment-ex-one.cidr_block}"
  ]
  from_port = 22
  to_port = 22
  protocol = "tcp"
  }
}
