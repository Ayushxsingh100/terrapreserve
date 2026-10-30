output "sg_ids" {
  value = {
    for k, v in aws_security_group.rules: k => v.id
  }
}