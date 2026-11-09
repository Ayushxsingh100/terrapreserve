output "private_subnets" {
  value = [ for a in aws_subnet.privatesubnet : a.id ]
}

output "public_subnets" {
  value = [ for a in aws_subnet.publicsubnet : a.id ]
}