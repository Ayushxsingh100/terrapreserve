variable "my_ip" {
  description = "The IP address that is allowed access to the Security Group (typically your public IP)."
}

variable "cidr_blocks" {
  description = "A list of CIDR blocks and corresponding name tags for the VPC and subnets."
  type = list(object({
    cidr_block = string
    name       = string
  }))
}
