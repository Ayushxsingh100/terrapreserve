resource "aws_subnet" "sum-ait-priv-subnet-1" {
  vpc_id = "${var.vpc_id}"
  cidr_block = "${var.priv_cidr_block-1}"
  map_public_ip_on_launch = "false"
  tags = "${var.tags}"
}
