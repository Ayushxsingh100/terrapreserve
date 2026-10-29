resource "aws_subnet" "main" {
  vpc_id = var.vpc_id
  for_each = var.subnet_config

  cidr_block = each.value.cidr_block
  availability_zone = each.value.az

  depends_on = [ var.vpc_id ]
  tags = {
    Name = each.key
  }
}

