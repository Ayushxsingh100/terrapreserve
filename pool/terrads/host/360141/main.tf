resource "aws_vpc" "my-main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = false
  enable_dns_support   = true
  instance_tenancy     = "default"

  tags = {
    Name = "my-main"
    team = "devops"
  }
}


data "aws_availability_zones" "available" {}


resource "aws_subnet" "my-private1" {
  vpc_id                  = "${aws_vpc.my-main.id}"
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${data.aws_availability_zones.available.names[0]}"
  map_public_ip_on_launch = true

  tags = {
    Name = "my-private1"
    team = "devops"
  }
}

resource "aws_route_table" "my-rt" {
  vpc_id = "${aws_vpc.my-main.id}"
  
  tags = {
    Name = "my-rt"
    team = "devops"
  }
}

resource "aws_route_table_association" "my-private1" {
  subnet_id      = "${aws_subnet.my-private1.id}"
  route_table_id = "${aws_route_table.my-rt.id}"
}