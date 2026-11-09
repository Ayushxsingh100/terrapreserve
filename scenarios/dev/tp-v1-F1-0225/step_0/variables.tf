variable "vpc_config" {
	description = "Enter the cidr block"
	type = object({
		cidr_block = string
		name = string
	})
	validation {
	    condition = can(cidrnetmask(var.vpc_config.cidr_block))
	    error_message = "Invalid CIDR format - ${var.vpc_config.cidr_block} it should be like this 0.0.0.0/0" 
	}
}
variable "subnet_config" {
	description = "Get the cidr and az for subnets"
	type = map(object({
		cidr_block =string
		az = string
		public = optional(bool,false)
}))
	     validation {
            condition = alltrue([for config in var.subnet_config : can(cidrnetmask(config.cidr_block))])
            error_message = "Invalid CIDR format  it should be like this 0.0.0.0/0"
        }

}
