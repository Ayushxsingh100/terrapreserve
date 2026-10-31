output "security_groups_detail" {
  value = ["${aws_security_group.sg}"]
}

output "security_groups_id" {
  value = tomap(
    {
      for sg in aws_security_group.sg: sg.name => sg.id
    }
  )
}
