#####################
# Account Variables #
#####################
variable "account_profile" {
  description = "The AWS profile used when managing the account"
  type        = string
}

variable "account_id" {
  description = "The AWS account id of the account that resources will be deployed into"
  type        = string
}
#################
# VPC Variables #
#################
variable "vpc_name" {
  description = "The name of the VPC being created"
  type        = string
  default     = "millennium-falcon"
}

variable "vpc_cidr" {

}

variable "public_subnet_cidr" {

}

variable "private_subnet_cidr" {

}
########
# TAGS #
########
variable "tag_product" {
  description = "Value of the Product tag"
}

variable "tag_sub_product" {
  description = "Value of the Sub-Product tag"
}

variable "tag_description" {
  description = "Value of the Description tag"
}

variable "tag_orchestration" {
  description = "Location of terraform control repo"
}

variable "tag_contact" {
  description = "Contact details of engineering lead"
}

variable "tag_environment" {
  description = "Value of the Environment tag"
}

variable "tag_constcode" {
}