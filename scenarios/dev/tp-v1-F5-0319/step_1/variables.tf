variable "environment" {
  description = "The name of the environment"
  type        = string
}

variable "project" {
  description = "The name of the project"
  type        = string  

}

variable "tags" {
  description = "The tags for the resource"
  type        = map(string)
}

variable "type" {
  description = "The type (priv or pub) of the subnet, rulting name will be in the form <environment>-<project>-<type>-<az>"
  type        = string  
}

variable "cidrs" {
  description = "List of cidrs, for every az one is required, i.e. 10.0.0.0/24 and 10.0.1.0/24"
  type        = list
}

variable "availability_zones" {
  description = "List of availability zones, i.e. ap-southeast-2a and ap-southeast-2b"
  type        = list
}

variable "vpc_id" {
  description = "VPC id"
  type        = string
}
