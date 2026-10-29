output "vpc_id" {
  value = aws_vpc.main_vpc.id
}

output "vpc_subnet_ids" {
  value = [aws_subnet.main_vpc_public_subnet.id, aws_subnet.main_vpc_public_subnet2.id]
}

output "public_subnet_id" {
  value = aws_subnet.main_vpc_public_subnet.id
}


# output "private_subnet_id" {
#   value = aws_subnet.subnet2.id
# }
