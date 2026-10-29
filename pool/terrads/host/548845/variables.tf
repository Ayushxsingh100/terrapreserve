# Define variables for security group configuration

# String variable for security group name with a default value
variable "sg_name" {
  type    = string
  default = "allow_ssh_http_https"  # Default security group name
}

# String variable for security group description with a default value
variable "sg_description" {
  type    = string
  default = "Allow ssh_http_https inbound traffic and all outbound traffic"  # Default security group description
}

# Map variable for security group tags with a default value
variable "sg_tag" {
  type    = map(string)
  default = {
    "Name" = "Cheche_security_group"  # Default tag "Name" with value "Cheche_security_group"
  }
}
