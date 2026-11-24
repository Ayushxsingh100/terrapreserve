# variables.tf
variable "vpc_cidr_block" {
  type        = string
  description = "CIDR block for the VPC you want to create"
  default     = "10.0.0.0/16"
}

variable "vpc_tags" {
  description = "Tags to assign to the VPC"
  type        = map(any)
  default = {
    Name = "main"
  }
}

variable "subnets" {

  type = map(object({
    az     = string
    name   = string
    public = bool
    tags   = map(string)
    cidr   = string
  }))
  default = {
    internal = {
      az     = "us-east-1a"
      name   = "internal"
      public = false
      tags = {
        Name = "internal"
      }
      cidr = "10.0.1.0/24"
    }
    external = {
      az     = "us-east-1a"
      name   = "external"
      public = true
      tags = {
        Name = "external"
      }
      cidr = "10.0.2.0/24"
    }

  }
}
