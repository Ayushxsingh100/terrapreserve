output "firewall_1_id" {
  description = "The ID from the Firewall"
  value = aws_security_group.firewall-1.id
}

output "ec2_sg_id" {
  description = "The ID from the EC2 security group"
  value = aws_security_group.ec2_sg.id 
}

output "alb_sg_id" {
  description = "The ID from the ALB security group"
  value = aws_security_group.alb_sg.id
}

output "ec2_to_alb_sg_id" {
  description = "The ID from the ec2 to alb egress rules"
  value = aws_security_group_rule.ec2_to_alb.id
}

output "alb_to_ec2_sg_id" {
  description = "The ID from the alb to the ec2 ingress rules "
  value = aws_security_group_rule.alb_to_ec2.id
}

output "ssm_sg_id" {
  description = "The ID from the ssm_endpoint_sg"
  value = aws_security_group.ssm_sg.id
}
