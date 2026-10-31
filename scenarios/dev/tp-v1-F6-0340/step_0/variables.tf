variable "security_group_name" {
  description = "name of security group to label in aws console"
  type = string
  default = "CHANGE THIS VARIABLE for module vpc_security_group "
}
variable "vpc_id" {
  description = "ID of vpc to attach this security group to"
}