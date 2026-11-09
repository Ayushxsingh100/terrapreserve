variable "subnet_config" {
  description = "Get CIDR and AZ of each subnet from User"
  type = map(object({
    cidr_block = string
    az = string
    # you can make it public if you want, but it's private by default
    public = optional(bool, false)
  }))

  validation {
    condition = alltrue([for config in var.subnet_config: can(cidrnetmask(config.cidr_block))])
    error_message = "Invalid CIDR Format!}"
  }
}

variable "vpc_id" {
  description = "Get from VPC module"
}