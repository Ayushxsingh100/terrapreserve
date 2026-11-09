output "vpc_arn" {
  value       = aws_vpc.main.arn
  description = "Amazon Resource Name (ARN) of VPC"
}
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "The ID of the VPC"
}
output "private_subnet_ids" {
  value       = local.private_subnet_ids
  description = "Map of Private Subnet and associated subnet id created.`private_subnet_ids = {\"Web or Data Subnet 1\" = { \"subnet_id\" = \"subnet-xxxxxxx\"}`"
}
output "public_subnet_ids" {
  value       = local.public_subnet_ids
  description = "Map of Public Subnet and associated subnet id created.`public_subnet_ids = {\"Public Subnet 1\" = { \"subnet_id\" = \"subnet-xxxxxxx\"}`"
}
output "subnets" {
  value = {
    for val in aws_subnet.main :
    val.tags.Name => val.cidr_block
  }
  description = "CIDR information associated with each subnet."
}
output "route_az1_map" {
  value       = local.route_az1_map
  description = "Route Mapping for Availability Zone 1 (Required by routes module)"
}
output "route_az2_map" {
  value       = local.route_az2_map
  description = "Route Mapping for Availability Zone 2 (Required by routes module)"
}
output "route_az3_map" {
  value       = local.route_az3_map
  description = "Route Mapping for Availability Zone 3 (Required by routes module)"
}
