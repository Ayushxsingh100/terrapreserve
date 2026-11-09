locals {
  calculated_subnet_size_list = length(var.subnet_size_override_list) > 0 ? var.subnet_size_override_list : [for i in range(var.subnet_count) : 24]

  subnet_mask = split("/", aws_vpc.this.cidr_block)[1]

  subnet_mask_bits = [for i in range(length(local.calculated_subnet_size_list)) : local.calculated_subnet_size_list[i]-local.subnet_mask]

  subnet_cidrs = cidrsubnets(aws_vpc.this.cidr_block, local.subnet_mask_bits... )
}

resource "aws_subnet" "this" {
  count             = length(local.subnet_cidrs)
  vpc_id = aws_vpc.this.id
  cidr_block        = local.subnet_cidrs[count.index]
  availability_zone = element(data.aws_availability_zones.available.names, count.index % length(data.aws_availability_zones.available.names))
  tags = {
    Name = "subnet-${var.name}-${count.index}"
  }
}