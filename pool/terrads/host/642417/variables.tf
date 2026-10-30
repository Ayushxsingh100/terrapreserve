variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string
}

variable "bastion_vpc_cidr" {
  description = "CIDR block of the bastion VPC"
  type        = string
}

variable "my_ip" {
  description = "Your IP address for SSH access"
  type        = string
}

variable "enable_vpc_peering" {
  description = "Whether VPC peering is enabled"
  type        = bool
  default     = true
}

variable "name_prefix" {
  description = "Name prefix for security groups"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}