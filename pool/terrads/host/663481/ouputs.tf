output "vpc_link_sg" {
  value = aws_security_group.vpc_link_sg.id
}

output "lb_sg" {
  value = aws_security_group.lb_sg.id
}

output "ecs_sg" {
  value = aws_security_group.ecs_sg.id
}

output "vpc_endpoint_sg" {
  value = aws_security_group.vpc_endpoint.id
}
