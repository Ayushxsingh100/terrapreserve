output "sg_id" {
  value = aws_security_group.my_sg.*.id
}

output "sg_arn" {
  value = aws_security_group.my_sg.*.arn
}

output "cidr_sg_id" {
  value = aws_security_group.cidr_sg.*.id
}

output "cidr_sg_arn" {
  value = aws_security_group.cidr_sg.*.arn
}

