variable "name" {
  description = "The name of the security group"
  type        = string
}

variable "default_vpc_id" {
  description = "The ID of the default VPC to use"
  type = string
}

variable "description" {
  description = "The description of the security group, may be null"
  type        = string
  default     = null
}

variable "tags" {
  description = "The tags to apply the security group, may be empty"
  type        = map(string)
  default     = {}
}

variable "egress_rules" {
  description = "A list of egress rules, if empty no outbound traffic"
  type = list(object({
    from_port          = number
    to_port            = number
    protocol           = string
    cidr_blocks        = list(string)
    ipv6_cidr_blocks   = list(string)
    security_group_ids = list(string)
  }))
  default = []
}

variable "egress_allow_all" {
  description = "Overrides egress_rules attribute to allow all outbound traffic"
  type        = bool
  default     = false
}

variable "ingress_rules" {
  description = "A list of ingress rule"
  type = list(object({
    from_port          = number
    to_port            = number
    protocol           = string
    cidr_blocks        = list(string)
    ipv6_cidr_blocks   = list(string)
    security_group_ids = list(string)
  }))
  default = []
}
