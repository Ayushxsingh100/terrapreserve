variable "aws_config" {
    description = "To get cidr and name of vpc from user"
    type = object({
      cidr_block = string
      Name = string
    })
  
}

variable "subnet_config" {
    description = "To get cidr and AZ for subnet"
    # subnet 1 (cidr=.. az=..)
    type = map(object({
      cidr_block = string
      az = string
      public = optional( bool, false)
    }))
  
}