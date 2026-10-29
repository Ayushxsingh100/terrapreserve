variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"


}

variable "vpc_name" {
  type    = string
  default = "this"
}



variable "vpc_config" {


  description = <<EOT

  cidr_block: The CIDR block of the subnet
  public: Wether the subnet should,,.,....
  az:   the    

EOT
  type = object({
    cidr_block = string
    name       = string
  })
  default = {
    cidr_block = "10.0.0.0/16"
    name       = "default-vpc"
  }
  validation {
    condition     = can(cidrnetmask(var.vpc_config.cidr_block))
    error_message = "The vpc_cidr must contain a valid CIDR block------------"
  }

}

variable "subnet_config" {
  type = map(object({
    cidr_block = string
    public     = optional(bool, false)
    az         = string
  }))



  default = {
    "subnet_az1_public" = {
      cidr_block = "10.0.1.0/24"
      az         = "us-east-1a"
    }
    "subnet_az1_private" = {
      cidr_block = "10.0.2.0/24"
      az         = "us-east-1a"
    }
    "subnet_az2_public" = {
      cidr_block = "10.0.3.0/24"
      az         = "us-east-1b"
    }
    "subnet_az2_private" = {
      cidr_block = "10.0.4.0/24"
      az         = "us-east-1b"
    }
  }

  validation {
    condition = alltrue([
      for config in values(var.subnet_config) : can(cidrnetmask(config.cidr_block))
    ])
    error_message = "The cidr_block config option must contain a valid CIDR block"
  }
}
