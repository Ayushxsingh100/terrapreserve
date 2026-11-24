variable "vpc_config" {
  description = "To get the CIDR and Name of form the user"
  type        = object({
    name = string
    cidr_block = string
  })
  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "The provided CIDR block is not valid - ${var.vpc_config.cidr_block}"
  }
  
}

variable "subnet_config" {
    #subnet1={cidr=.. az} subnet2={} subnet3={}
  description = "To get the CIDR and AZ for the subnets"
  type = map(object({
    name = string
    cidr_block = string
    availability_zone = string
    public = optional(bool, false)
  }))
  validation {
    #sub1={cidr} sub2{cidr=..}, [true, true, false]
    condition     = alltrue([for config in var.subnet_config : can(cidrnetmask(config.cidr_block))])
    error_message = "The provided CIDR block is not valid"
  }
  
  
}