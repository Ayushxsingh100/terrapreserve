variable "vpc_id" {
  type        = string
  description = "The ID of the VPC in which to attach the security group"
}

variable "sg_name_prefix" {
  type        = string
  description = "Prefix for security group names"
}

variable "ingress_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks to attach to security groups for ingress"
  default     = []
}

variable "ingress_security_groups" {
  type        = list(string)
  description = "Existing security groups to attach to new security groups for ingress"
  default     = []
}

variable "egress_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks to attach to security groups for egress"
  default     = []
}

variable "egress_security_groups" {
  type        = list(string)
  description = "Existing security groups to attach to new security groups for egress"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to add to all resources."
  default     = {}
}

variable "ingress_ports" {
  type        = list(number)
  description = "Ports to create ingress traffic rules for"
}

variable "maximum_rules_per_sg" {
  type        = number
  description = "Maximum number of rules for each security group"
  default     = 50
}

variable "ingress_protocol" {
  type        = string
  description = "Protocol for ingress rules. If not icmp, icmpv6, tcp, udp, or all use the protocol number."
}

variable "egress_protocol" {
  type        = string
  description = "Protocol for egress rules. If not icmp, icmpv6, tcp, udp, or all use the protocol number."
}
