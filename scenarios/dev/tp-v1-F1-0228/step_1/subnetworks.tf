
resource "aws_subnet" "subnet1" {
  cidr_block = "${cidrsubnet(aws_vpc.terraform-env-example.cidr_block, 3, 1)}"
  vpc_id = "${aws_vpc.terraform-env-example.id}"
  availability_zone = "ap-southeast-1a"
}

resource "aws_subnet" "subnet2" {
  cidr_block = "${cidrsubnet(aws_vpc.terraform-env-example.cidr_block, 2, 2)}"
  vpc_id = "${aws_vpc.terraform-env-example.id}"
  availability_zone = "ap-southeast-1b"
}

resource "aws_security_group" "sg_subnet" {
  vpc_id = "${aws_vpc.terraform-env-example.id}"

  ingress {
    cidr_blocks = [
      "${aws_vpc.terraform-env-example.cidr_block}"
    ]

    from_port = 80
    to_port = 80
    protocol = "tcp"
  }

}
