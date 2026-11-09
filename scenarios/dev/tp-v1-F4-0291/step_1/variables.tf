variable "vpc_id" {
  description = "The VPC ID where subnets will be created"
  type        = string
}
variable "azs" {
  description = "List of Availability Zones"
  type        = list(string)
}
variable "public_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}
variable "private_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
}