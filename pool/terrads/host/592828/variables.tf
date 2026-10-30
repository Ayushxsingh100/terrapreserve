
variable "vpc_config" {
  description = "Variable contains the VPC config. Contains cidr_block & VPC name"
  type = object({
    cidr_block = string
    name       = string
  })
  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "The variable cidr_block must contain a valid cidr block"
  }
}

variable "subnet_config" {
  description = "Variable for Subnet config. Contains cidr_block, Az & access to public or not "
  type = map(object({
    cidr_block = string
    az         = string
    public     = optional(bool, false)
  }))

  validation {
    condition = alltrue([
      for config in values(var.subnet_config) : can(cidrnetmask(config.cidr_block))
    ])
    error_message = "The variable cidr_block must contain a valid cidr block"
  }

}