# ==================================================================
# AWS INTERNET GATEWAY
# ==================================================================
resource "aws_internet_gateway" "test_igw" {
  vpc_id = aws_vpc.test_vpc.id

  tags = {
    Name = "test-services-igw"
  }
}