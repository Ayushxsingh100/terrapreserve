variable "web_port" {
  description = "The port the web server is listening on"
  type        = number
}

variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "vpc_id" {
  description = "The ID of the VPC to deploy the security group to"
  type        = string
}
