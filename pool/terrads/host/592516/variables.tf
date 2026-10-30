variable "sg_name" {
  type        = string
  description = "name for security group for ec2"
}
variable "vpc_id" {
  type        = string
  description = "main vpc id"
}
variable "nat_gateway_eip" {
  type        = list(string)
  description = "NAT gateway Elastic IP addresses"
}

variable "load_balancer_security_group_id" {
  type        = string
  description = "lb sg id for set destination"
}
