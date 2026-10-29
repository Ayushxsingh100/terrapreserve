output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnets" {
  value = aws_subnet.public[*].id
}

output "data_subnets" {
  value = aws_subnet.data[*].id
}

output "app_subnets" {
  value = aws_subnet.app[*].id
}