variable "vpc_id" {
  description = "ID of the VPC where SG is to be created"
  type        = string
}

variable "app_port" {
  description = "Port on which the app will run"
  type        = number
  default = "3000"
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
