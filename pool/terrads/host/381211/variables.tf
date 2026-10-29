variable "name" {
  type        = string
  default     = ""
}

variable "cidr" {
  type        = string
  default     = "0.0.0.0/0"
}

variable "azs" {
  type    = list(string)
  default = []
  
}

variable "use_az_id" {
  type    = list(string)
  default = ["use1-az1", "use1-az2", "use1-az3", "use1-az4"]
  
}

variable "azs_count" {
  type    = number
  default = "4"
  
}

variable "public_subnets" {
  type        = list(string)
  default     = []
}

variable "private_subnets" {
  type        = list(string)
  default     = []
}

variable "endpoint_subnets" {
  type        = list(string)
  default     = []
}

##
