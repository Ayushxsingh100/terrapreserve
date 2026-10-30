variable "vpc_config" {
  description = "To get the CIDR and Name of VPC from User"
  type = object({
    cidr_block = string
    name       = string
  })
  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "Invalid cidr block - ${var.vpc_config.cidr_block}"
  }
}

variable "subnet_config" {
  # sub1 = { cidr, az} , sub2 = {cidr,az}
  description = "Get CIDR and AZ for the sunets"
  type = map(object({
    cidr_block        = string
    availability_zone = string
    public            = optional(bool, false)
  }))
  validation {
    # sub1 = {cidr =} , sub2 = {}, sub3 = {}
    condition     = alltrue([for config in var.subnet_config : can(cidrnetmask(config.cidr_block))])
    error_message = "Invalid cidr block - ${var.vpc_config.cidr_block}"
  }
}
