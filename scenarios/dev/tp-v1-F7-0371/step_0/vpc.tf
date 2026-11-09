resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  enable_dns_hostnames = true

  # tags = {
  #   Name              = var.vpc_name
  #   Product       = var.tag_product
  #   Sub_product   = var.tag_sub_product
  #   Description   = var.tag_description
  #   Orchestration = var.tag_orchestration
  #   Environment   = var.tag_environment
  #   Contact       = var.tag_contact
  # }

  tags = merge(
    {
      Name = var.vpc_name,
    },
    local.common_tags
  )
}

resource "aws_subnet" "public_subnet" {
  vpc_id     = aws_vpc.main.id
  cidr_block = var.public_subnet_cidr

  # Allows instances in this subnet to be assigned public IP addresses by default
  map_public_ip_on_launch = true

  # tags = {
  #   Name = "example-public-subnet"
  # }
  tags = merge(
    {
      Name = "example-public-subnet"
    },
    local.common_tags
  )
}

resource "aws_subnet" "private_subnet" {
  vpc_id     = aws_vpc.main.id
  cidr_block = var.private_subnet_cidr

  map_public_ip_on_launch = false

  # tags = {
  #   Name = "example-private-subnet"
  # }
  tags = merge(
    {
      Name = "example-private-subnet"
    },
    local.common_tags
  )
}