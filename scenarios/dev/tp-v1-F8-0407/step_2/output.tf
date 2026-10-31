output "alb_sg_id" {
  value = aws_security_group.alb_sg.id
}
output "ecs_sg_id" {
  value = aws_security_group.ecs_sg.id
}

output "db_sq_id" {
  value = aws_security_group.db-security-group.id
}