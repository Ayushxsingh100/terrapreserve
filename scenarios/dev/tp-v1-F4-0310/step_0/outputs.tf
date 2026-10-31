output "vm_sg_name" {
  value = aws_security_group.btc.name
}

output "elb_sg_id" {
  value = aws_security_group.btc_lb.id
}