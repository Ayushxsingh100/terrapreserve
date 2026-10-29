variable "vpc_config" {
  description = "To get the CIDR and Name of the VPC"
  type = object({
    cidr_block = string
    Name       = string
  })

  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "Invalid CIDR - ${var.vpc_config.cidr_block}"
  }
}

variable "subnet_config" {
  description = "To get the CIDR and AZ of the Subnet"
  type = map(object({
    cidr_block = string
    az         = string
    public     = optional(bool, false)  #Default value false hoga
  }))

  validation {
    condition = alltrue([
      for config in values(var.subnet_config) : can(cidrnetmask(config.cidr_block))   #can() returns boolean
    ])                                                                              #cidrnetmask() defines the structure 
    error_message = "Invalid CIDR block in subnet_config"
  }
}
