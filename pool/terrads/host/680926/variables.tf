variable "vpc_config" {
  description = "Contains the VPC configuration like cidr_block and name"
  type = object({
    cidr_block = string
    name       = string
  })

  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block)) # cidrnetmask function checks for valid CIDR notation
    error_message = "Provided CIDR block is not valid."
  }
}


variable "subnet_config" {
  description = "Contains Subnet configuration like cidr_block, availability zone and whether it's public or private"
  type = map(object({
    cidr_block = string
    public     = optional(bool, false)
    az         = string
  }))

  validation {
    condition = alltrue([
      for config in values(var.subnet_config) : can(cidrnetmask(config.cidr_block))
    ])
    error_message = "Provided CIDR block is not valid."
  }
}
