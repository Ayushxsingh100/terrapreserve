variable "resource_tags" {
  description = "default tags for all the module resources"
  type        = map(string)
  default = {
    terraform = "ec2-module"
  }
}
variable "vpc_cidr" {
  description = "default vpc cidr for lab module"
  type        = string
  default = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "list of private subnets from module"
  type        = map(any)
  default = {
    websubnet     = "10.0.1.0/24"
    dbsubnet      = "10.0.11.0/24"
    privatesubnet = "10.0.21.0/24"
  }
}
variable "public_subnets" {
  description = "list of private subnets from module"
  type        = map(any)
  default = {
    bastionsubnet     = "10.0.100.0/28"
    firewallsubnet      = "10.0.120.0/28"
    publicsubnet = "10.0.150.0/28"
  }
}