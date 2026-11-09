variable "vpc_id" {
  description = "ID of the main VPC where this subnets will be associated to."
  type        = string
}

variable "availability_zone" {
  description = "Availability zone to where this subnet will be created."
  type = string
}

variable "cidr_block" {
    description = "The CIDR block of this subnet."
    type = string
}

variable "nat_gw_id" {
    description = "ID of the NAT gateway that this subnet will route trafic to."
    type = string
}

variable "tags" {
  description = "A map of tags to add to all resources."
  type        = map(string)
}

variable "prefix" {
  description = "A prefix that will be appended to all resources."
  type        = string
}