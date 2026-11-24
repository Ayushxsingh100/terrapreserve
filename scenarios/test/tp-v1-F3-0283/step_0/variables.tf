variable "vpc_config" {
  description = "To get CIDR block and name of VPC from user"
  type = object({
    name       = string
    cidr_block = string
  })
}

variable "subnet_config" {
  description = "To get subnet config of vpc from user"
  type = map(object({
    cidr_block = string
    az         = string
    public = optional(bool, false)
  }))
}

