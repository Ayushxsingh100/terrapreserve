output "subnets" {
  value = [aws_subnet.private1.id, aws_subnet.private2.id, aws_subnet.private3.id]
}

output "route_tables" {
  value = [aws_route_table.private1.id, aws_route_table.private2.id, aws_route_table.private3.id]
}
