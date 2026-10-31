output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "subnets" {
  value = aws_subnet.private_subnets
}
