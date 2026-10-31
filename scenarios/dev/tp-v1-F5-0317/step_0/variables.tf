variable "sg_name" {
  type        = string
  description = "Security group name"
}

variable "sg_description" {
  type        = string
  description = "Security group description. "
}

variable "vpc_id" {
  type        = string
  description = "Vpc Id where securitygroup should be used to create"
}

variable "ingress_ports" {
  type        = list(any)
  description = "Ingress Ports"
}

variable "egress_ports" {
  type        = list(any)
  description = "Egress Ports"
}