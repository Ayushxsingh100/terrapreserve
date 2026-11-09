variable "region" {
  type        = string
  default     = "ap-south-1"
  description = "variable for region of aws"
}
variable "network" {
  description = "Network with name and cidr"
  type = object({
    name = string
    cidr = string
  })
  default = {
    name = "king"
    cidr = "192.168.0.0/16"
  }
}
variable "subnet_info" {
  description = "subnet info of vpc network"
  type = list(object({
    name = string
    cidr = string
    azs  = string
  }))
  default = [{
    azs  = "ap-south-1a"
    cidr = "192.168.0.0/24"
    name = "car"
    },
    {
      azs  = "ap-south-1b"
      cidr = "192.168.1.0/24"
      name = "car-2"
    },
    {
      azs  = "ap-south-1c"
      cidr = "192.168.2.0/24"
      name = "db"
    },
    {
      azs  = "ap-south-1a"
      cidr = "192.168.3.0/24"
      name = "app"
    },
    {
      azs  = "ap-south-1b"
      cidr = "192.168.4.0/24"
      name = "web"
    }
  ]
}