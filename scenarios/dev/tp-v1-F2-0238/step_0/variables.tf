variable "vpc_config" {
    description = "To get cidr and name of vpc from the user"
    type = object({
      cidr_block=string
      name = string
    })

}

variable "subnet_config" {
    description="Get cidr_block and availability zones"
    type=map(object({
      cidr_block = string
      az=string
      public=optional(bool,false)
    }))  
    validation{
    condition = alltrue([for config in var.subnet_config:can(cidrnetmask(config.cidr_block))])
    error_message = "Invalid cidr format-${var.vpc_config.cidr_block}"
    }
}