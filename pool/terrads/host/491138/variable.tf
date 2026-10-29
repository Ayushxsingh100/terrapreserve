variable "region" {
  default = "us-east-1"
}
variable "ingressCIDRblock" {
  type    = list(any)
  default = ["0.0.0.0/0"]
}
variable "security_group_name" {
  default = "my_security_group"
}
