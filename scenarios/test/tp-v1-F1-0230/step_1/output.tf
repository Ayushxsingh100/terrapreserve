# ==================================================================
# AWS VPC OUTPUTS
# ==================================================================
output "vpc_id" {
  description = "ID da VPC criada"
  value       = aws_vpc.test_vpc.id
}

output "vpc_cidr_block" {
  description = "CIDR block da VPC"
  value       = aws_vpc.test_vpc.cidr_block
}

output "subnet_id" {
  description = "ID da subnet criada"
  value       = aws_subnet.test_subnet.id
}

output "subnet_cidr_block" {
  description = "CIDR block da subnet"
  value       = aws_subnet.test_subnet.cidr_block
}

output "internet_gateway_id" {
  description = "ID do Internet Gateway"
  value       = aws_internet_gateway.test_igw.id
}

output "route_table_id" {
  description = "ID da Route Table"
  value       = aws_route_table.test_rt.id
}

output "route_table_association_id" {
  description = "ID da associação da Route Table com a Subnet"
  value       = aws_route_table_association.my_route_table_association.id
}