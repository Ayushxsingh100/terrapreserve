# The security group Id's that will be used to pass on other resources 
output "trident_web_alb_sg_id" {
  value = aws_security_group.trident_web_alb_sg.id
}

output "trident_web_sg_id" {
  value = aws_security_group.trident_web_sg.id
}

output "trident_app_alb_sg_id" {
  value = aws_security_group.trident_app_alb_sg.id
}

output "trident_app_sg_id" {
  value = aws_security_group.trident_app_sg.id
}

output "trident_data_sg_id" {
  value = aws_security_group.trident_data_sg.id
}

output "sg_ids" {
  value = {
    web_alb = aws_security_group.trident_web_alb_sg.id
    web     = aws_security_group.trident_web_sg.id
    app_alb = aws_security_group.trident_app_alb_sg.id
    app     = aws_security_group.trident_app_sg.id
    data    = aws_security_group.trident_data_sg.id
  }
}
