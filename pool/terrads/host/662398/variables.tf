variable "vpc_id" {
  type        = string
  description = "ID of the VPC where the security group will be created"
}

variable "project" {
  type        = string
  description = "Name of the project for resource tagging"
}

variable "environment" {
  type        = string
  description = "Name of the environment (global or other)"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR from which SSH access will be allowed"
  default     = "0.0.0.0/0"
}

variable "name" {
  type = string
}

variable "description" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {"CreatedBy" = "terraform"}
}

variable "ingress_rules" {
  type = map(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
  }))
  default = {}
}

variable "egress_rules" {
  type = map(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
  }))
  default = {
    default = {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}
