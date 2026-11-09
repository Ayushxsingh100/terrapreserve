variable "cidr_block" {
  type        = string
  default     = ""
  description = "Please provide CIDR block for VPC"
}
variable "region" {
  type        = string
  default     = ""
  description = "Please provide a region for provider"
}
variable "tags" {
  type        = map(any)
  default     = {}
  description = "Please provide a tag for resources"
}
variable "public_subnet1" {
  type        = string
  default     = ""
  description = "Please provide public subnet CIDR block"
}
variable "public_subnet2" {
  type        = string
  default     = ""
  description = "Please provide public subnet CIDR block"
}
variable "public_subnet3" {
  type        = string
  default     = ""
  description = "Please provide public subnet CIDR block"
}

variable "private_subnet1" {
  type        = string
  default     = ""
  description = "Please provide private subnet CIDR block"
}
variable "private_subnet2" {
  type        = string
  default     = ""
  description = "Please provide private subnet CIDR block"
}
variable "private_subnet3" {
  type        = string
  default     = ""
  description = "Please provide private subnet CIDR block"
}