output "sg-web" {
  value = aws_security_group.sg_projeto_web
}

output "sg-db" {
  value = aws_security_group.sg_projeto_db
}

output "sg-elb" {
  value = aws_security_group.sg_projeto_elb
}

output "sg-cache" {
  value = aws_security_group.sg_projeto_cache
}

output "sg-all" {
  value = aws_security_group.sg_projeto_all
}