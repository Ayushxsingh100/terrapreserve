# ==================================================================
# AWS VIRTUAL PRIVATE CLOUD - VPC
# ==================================================================
resource "aws_vpc" "test_vpc" {
  cidr_block           = "10.0.0.0/20"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "test-services-vpc"
  }
}