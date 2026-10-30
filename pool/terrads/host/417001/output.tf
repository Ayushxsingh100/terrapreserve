output "vpc_cidr" {
  description = "cidr vpc IP"
  value       = aws_vpc.vpc_cidr[*].cidr_block
}

output "vpc_subnets" {
  description = "vpc subnets IP"
  value = {
    for k, v in aws_subnet.subnet : k => v.id
  }
}