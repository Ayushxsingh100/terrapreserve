resource "aws_internet_gateway" "igw_main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.env}-${var.aws_region}-${var.app_name}-igw"
      Tier = "public"
    }
  )
}