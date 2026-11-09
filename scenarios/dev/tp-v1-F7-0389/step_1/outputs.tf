output "vpc_id" {
  value = aws_vpc.taskplanner_vpc.id
}

output "public_subnets_ids" {
  value = aws_subnet.taskplanner_public_subnet[*].id
}

output "private_subnets_ids" {
  value = aws_subnet.taskplanner_private_subnet[*].id
}

output "lb_security_group_id" {
  value = aws_security_group.taskplanner_security_group.id
}
