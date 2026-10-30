# Specify values as output of this module 
# so vars in this module can be called by other child modules (web module in this case)

output "public_subnet" {
  value = aws_subnet.dev_cicd_vpc_public_subnet.id
}

output "security_group" {
  value = aws_security_group.dev_cicd_vpc_public_subnet_security_group.id
}