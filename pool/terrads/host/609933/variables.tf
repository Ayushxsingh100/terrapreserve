variable "stack_name" {
  description = "Name of the stack"
  type        = string
}

variable "env" {
  description = "Name of the environment"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "aws_region" {
  description = "AWS region to use"
  type        = string

  validation {
    condition     = var.aws_region == "us-gov-east-1" || var.aws_region == "us-gov-west-1"
    error_message = "aws_region must be one of: us-gov-east-1 or us-gov-west-1."
  }
}

variable "stack_tool" {
  description = "SIG tools"
  type        = string
}

variable "ingress_rules" {
  description = "List of ingress rule objects."
  type = list(object({
    description      = string
    from_port        = number
    to_port          = number
    protocol         = string
    cidr_blocks      = list(string)
    ipv6_cidr_blocks = list(string)
    security_groups  = list(string)
  }))
  default = []
}

variable "egress_rules" {
  description = "List of egress rule objects."
  type = list(object({
    description      = string
    from_port        = number
    to_port          = number
    protocol         = string
    cidr_blocks      = list(string)
    ipv6_cidr_blocks = list(string)
  }))
  default = []
}