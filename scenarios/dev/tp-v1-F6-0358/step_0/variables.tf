variable "vpc_config" {
  description = "Configuration for the vpc"
  type = object({
    cidr_block = string
    region     = string
    name       = string
  })

  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "The provided CIDR block is not valid"
  }
}


variable "subnet_config" {
  description = "Configuration for the subnet"
  type = map(object({
    cidr_block = string
    az         = string
    is_public  = optional(bool, false)
  }))

  validation {
    # expected format : subnet1 = {cidr_block=...,az=...} subnet2 = {cidr_block=...,az=...}     [true true false]
    condition     = alltrue([for config in var.subnet_config : can(cidrnetmask(config.cidr_block))])
    error_message = "The provided CIDR block is not valid"
  }
}
