output "private_subnet_1_id" {
  value = aws_subnet.private_subnet_1.id
}

output "private_subnet_2_id" {
  value = aws_subnet.private_subnet_2.id
}

output "public_subnet_ids" {
  value = [
    aws_subnet.public_subnet_1.id,
    aws_subnet.public_subnet_2.id
  ]
}


output "vpc_id" {
  value = aws_vpc.main_vpc.id
}


output "db_subnet_group" {
  value = aws_db_subnet_group.main.name
}