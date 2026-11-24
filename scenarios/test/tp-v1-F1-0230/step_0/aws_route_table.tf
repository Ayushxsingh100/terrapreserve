# ==================================================================
# AWS ROUTE TABLE
# ==================================================================
resource "aws_route_table" "test_rt" {
  vpc_id = aws_vpc.test_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.test_igw.id
  }

  tags = {
    Name = "test-services-rt"
  }
}

# ==================================================================
# AWS ROUTE TABLE ASSOCIATION
# ==================================================================
resource "aws_route_table_association" "my_route_table_association" {
  subnet_id      = aws_subnet.test_subnet.id
  route_table_id = aws_route_table.test_rt.id
}