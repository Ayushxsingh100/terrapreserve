output "vpc_id" {
    value = aws_vpc.vpc.id
}

output "public_subnet1_id" {
    value = aws_subnet.public-subnet1.id
}

output "public_subnet2_id" {
    value = aws_subnet.public-subnet2.id
}

output "private_subnet1_id" {
    value = aws_subnet.private-subnet1.id
}

output "private_subnet2_id" {
    value = aws_subnet.private-subnet2.id
}

output "private_route_table1_id" {
    value = aws_route_table.private-rt1.id
}

output "private_route_table2_id" {
    value = aws_route_table.private-rt2.id
}

