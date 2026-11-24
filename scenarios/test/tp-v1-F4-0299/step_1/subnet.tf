variable "subnet_cidr" {
  type = string
  default = "172.16.0.0/24"
}

variable "subnet_az" {
  type = string
  default = "us-west-2a"
}

locals {
  vpc_id = "<%=state.stateList.output.outputs.aws_vpc.value.id%>"
}
resource "aws_subnet" "subnet" {
  # vpc_id            = aws_vpc.vpc.id
  vpc_id = local.vpc_id
  cidr_block        = var.subnet_cidr
  availability_zone = var.subnet_az
}

output "aws_subnet" {
  value = aws_subnet.subnet
}