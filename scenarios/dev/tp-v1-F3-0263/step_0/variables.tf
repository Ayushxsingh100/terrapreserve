variable "accessible_from" {
    description = "List of allowed CIDR IPs that can access the infrastructure (e.g., ['192.168.1.1/32'])"  
    type = list(string)
    default = []
}

variable "vpc_id" {
  description = "The ID of the VPC where security groups will be created"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "private_subnet_cidr" {
  description = "CIDR block for the private subnet"
  type        = string
}

variable "prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "ingress_rules" {
  description = "List of ingress rules for the security group"
  type = list(object({
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks  = list(string)
  }))
  default = [
    {
      from_port  = 80
      to_port    = 80
      protocol   = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    },
    {
      from_port  = 443
      to_port    = 443
      protocol   = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  ]
}
