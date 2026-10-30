variable "region" {
  description = "Region"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost Center"
  type        = string
  default     = "challenge-terraform"
}

variable "owner" {
  description = "Owner"
  type        = string
  default     = "Jonathan Vega"
}

variable "env" {
  description = "Enviroment"
  type        = string
  default     = "dev"
}

variable "name" {
  description = "Name Instance"
  type        = string
}

variable "type" {
  description = "Type Instance"
  type        = string
}

variable "ami" {
  description = "AMI ID"
  type        = string
  default     = "ami-01b799c439fd5516a"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
}

variable "instance_type" {
  description = "Instance Type"
  type        = string
  default     = "t3.micro"
}
