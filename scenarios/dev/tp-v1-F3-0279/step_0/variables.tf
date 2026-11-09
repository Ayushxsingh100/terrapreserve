variable "vpc_config" {
  description = "To get the VPC configuration"
  type = object({
    cidr_block = string
    name       = string
  })
  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "The cidr_block must be a valid CIDR block."
  }
}

variable "subnet_config" {
  description = "values for subnet configuration"
  type = map(object({
    cidr_block = string
    az         = string
    public  = optional(bool, false)
  }))

  validation {
    condition     = alltrue([for config in var.subnet_config: can(cidrnetmask(config.cidr_block))])
    error_message = "The cidr_block must be a valid CIDR block."
  }
}
