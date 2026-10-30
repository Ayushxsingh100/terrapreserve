output "SG_allow_22_id" {
  value = "${ aws_security_group.allow_22.id }"
}

output "SG_allow_80_id" {
  value = "${ aws_security_group.allow_80.id }"
}

output "SG_allow_4567_id" {
  value = "${ aws_security_group.allow_4567.id }"
}
