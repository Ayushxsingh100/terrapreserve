variable "region" {
  type        = string
  description = "set the project region"
}

variable "instancetype" {
  type        = string
  description = "set the instance type"
}

variable "vpcname" {
  type        = string
  description = "set the vpc name"
}

variable "vpc_cidr_block" {
  type        = string
  default     = "10.0.0.0/16"
  description = "set the vpc_cidr_block"
}

variable "igwname" {
  type        = string
  description = "set the igwname"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.1.0/24"]
  description = "set the public subnet cidr"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.2.0/24"]
  description = "set the private subnet cidr"
}

variable "azs" {
  type        = list(string)
  description = "Availability Zones"
  default     = ["sa-east-1a"]
}

variable "instancename" {
  type        = string
  description = "set the instance name"
}

variable "keypairname" {
  type        = string
  description = "set the keypairname (must be in the same folder as the terraform files) "
}
