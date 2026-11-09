# This is where you put your variables declaration

locals {
  common_tags = {
    terraform_managed = var.terraform_managed
    environment       = var.environment
    cost_account      = var.cost_account
  }
}

variable "environment" {
  description = "Your Target Environment"
  type        = string
}

variable "cost_account" {
  description = "Cost Tag"
  type        = string
}

variable "terraform_managed" {
  description = "Managed By Terraform?"
  type        = bool
}

variable "vpc_cidr" {
  description = "CIDR Address for the VPC"
  type        = string
}

