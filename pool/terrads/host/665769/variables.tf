# VPC info

variable "region" {
  type        = string
  description = "region for the current template"
  default     = "us-east-1" #the default value that will be passed when user does not pass a value
}

variable "network_info" {
  description = "vpc and subnet info"
  # using a nested object variable
  type = object({
    name = string
    cidr = string
    # subnet variable is a list of objects
    private_subnets = list(object({
      name = string
      az   = string
      cidr = string
    }))
    public_subnets = list(object({
      name = string
      az   = string
      cidr = string
    }))
  })

  default = {
    name = "noptf"
    cidr = "10.0.0.0/16"
    public_subnets = [{
      name = "app1"
      cidr = "10.0.1.0/24"
      az   = "us-east-1a"
      },
      {
        name = "app2"
        cidr = "10.0.2.0/24"
        az   = "us-east-1b"
    }]
    private_subnets = [{
      name = "db1"
      cidr = "10.0.11.0/24"
      az   = "us-east-1a"
      },
      {
        name = "db2"
        cidr = "10.0.12.0/24"
        az   = "us-east-1b"
      }
    ]
  }
}

