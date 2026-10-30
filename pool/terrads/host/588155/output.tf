# contains output information of the cloud resources of FridayHITT company.

output "PublicInstancePublicIP" {
  description = "Public IP of Public Instance in public Subnet"
  value       = aws_instance.Lab1FridayHITTPublicEC2Instance.public_ip
}

output "JumpBoxInstancePublicIP" {
  description = "Public IP of Jump box Instance in public Subnet"
  value       = aws_instance.Lab1FridayHITTJumpBox.public_ip
}

output "PrivateEC2Instance" {
  description = "Private EC2 Instance in Private Subnet"
  value       = aws_instance.Lab1FridayHITTPrivateEC2Instance.id
}

output "PublicEC2Instance" {
  description = "Public EC2 Instance in Public Subnet"
  value       = aws_instance.Lab1FridayHITTPublicEC2Instance.id
}

output "JumpboxEC2Instance" {
  description = "Jump box EC2 Instance in Public Subnet"
  value       = aws_instance.Lab1FridayHITTJumpBox.id
}