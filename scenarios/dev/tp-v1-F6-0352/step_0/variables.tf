variable "security-group-name" {
  description = "Name of the security group"
  type = list(string)
}

variable "security-group-description" {
  description = "Description of the security group"
  type = list(string)
}

variable "vpc-id" {
  description = "ID of the vpc"
  type = string
}

variable "ingress-access" {
  description = "Ingress port, protocol and cidr to use for a security group"
  type = list(object({
    from-port = number
    to-port = number
    protocol = string
    cidr = string
    description = string
  }))
}

# variable "security-group-tags" {
#   description = "Tags to be attached to the security group"
#   type = list(maps)
# }