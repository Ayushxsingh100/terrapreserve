# -----------------------------------------------------------------------------
# File        : ctlabs-terraform/modules/aws/subnet/main.tf
# Description : subnet module
# -----------------------------------------------------------------------------


resource "aws_subnet" "sub" {
  for_each = { for sub in var.subnets : sub.name => sub }

  vpc_id            = var.tp_ds_aws_vpc_net[each.value.name].id
  cidr_block        = each.value.cidr
  availability_zone = var.project.zone
  tags              = { Name = each.value.name }

}
