variable "create_security_group" {
  description = "Whether to create a new security group or use an existing one"
  type        = bool
  default     = true
}

variable "name" {
  description = "The name of the security group"
  type        = string
  default     = null
}

variable "description" {
  description = "The description of the security group"
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "The VPC ID"
  type        = string
  default     = null
}

variable "ingress_rules" {
  description = "List of ingress rules"
  type = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
}

variable "egress_rules" {
  description = "List of egress rules"
  type = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
}

variable "tags" {
  description = "A map of tags to add to the security group"
  type        = map(string)
  default     = null
}
