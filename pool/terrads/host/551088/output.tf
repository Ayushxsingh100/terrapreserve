# output "security_group_ids" {
#   description = "The IDs of the security groups."
#   value = { for sg_name, sg_resource in aws_security_group.main : sg_name => sg_resource.id }
# }
output "security_group_ids" {
  value = [for sg in aws_security_group.main : sg.id]
}
