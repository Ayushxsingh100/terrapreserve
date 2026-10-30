#Define the VPC
resource "aws_vpc" "benchmarkt_vpc" {
  cidr_block = var.vpc_cidr

  tags = {
    Name        = var.vpc_name
    Environment = "benchmarkt_enviroment"
    Terraform   = "true"
  }
}

