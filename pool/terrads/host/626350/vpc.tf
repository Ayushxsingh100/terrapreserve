resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  tags = merge(
    var.tags,
    {
      Name = "${var.env}-${var.aws_region}-${var.app_name}-main-vpc"
    }
  )
}