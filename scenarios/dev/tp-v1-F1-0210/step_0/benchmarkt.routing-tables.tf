resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.benchmarkt_vpc.id

  tags = {
    Name      = "benchmarkt_private_rtb"
    Terraform = "true"
  }
}

resource "aws_route_table_association" "private" {
  depends_on     = [aws_subnet.private_subnets]
  route_table_id = aws_route_table.private_route_table.id
  for_each       = aws_subnet.private_subnets
  subnet_id      = each.value.id
}
