#output "myoutput" {
#  description = "Description of my output"
#  value       = "value"
#  depends_on  = [<some resource>]
#}

output "sec_id" {
  value = data.aws_security_group.newsg.id
}

output "instance_public_ip" {
  value       = ["${aws_instance.ec2_instance.*.public_ip}"]
  description = "The public IP address of the instance."
}
