# -----------------------------------------------------------------------------
# File        : ctlabs-terraform/modules/aws/subnet/main.tf
# Description : subnet module
# -----------------------------------------------------------------------------

data "aws_vpc" "net" {
  for_each = { for sub in var.subnets : sub.name => sub }

  tags = { Name = each.value.net }
}

resource "aws_subnet" "sub" {
  for_each = { for sub in var.subnets : sub.name => sub }

  vpc_id            = data.aws_vpc.net[each.value.name].id
  cidr_block        = each.value.cidr
  availability_zone = var.project.zone
  tags              = { Name = each.value.name }

}
