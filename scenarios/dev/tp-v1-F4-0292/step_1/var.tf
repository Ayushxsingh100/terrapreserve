variable "cidr_sg_name" {
  type        = list(string)
  description = "Naming the cdir sg group"
}

variable "sg_name" {
  type        = list(string)
  default     = [""]
  description = "Naming the security sg group"
}

variable "cidr_sg" {
  type        = list(map(any))
  description = "Cidr sg that will be created"
}

variable "sg" {
  type        = list(map(any))
  default     = [{}]
  description = "Security group sg that will be created"
}

variable "vpc_id" {
  type        = string
  description = "the id of the vpc"
}
