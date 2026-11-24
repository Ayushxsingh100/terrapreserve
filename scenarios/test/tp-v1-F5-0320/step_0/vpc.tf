resource "aws_vpc" "krasteki-vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true ## (Optional) A boolean flag to enable/disable DNS hostnames in the VPC. Defaults false. ##
  enable_dns_support   = true ## (Optional) A boolean flag to enable/disable DNS support in the VPC. Defaults true. ##
  tags = {
    Name = "${var.tag}-vpc"
  }
}
