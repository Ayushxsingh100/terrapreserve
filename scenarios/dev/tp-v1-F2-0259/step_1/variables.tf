variable "vpc_name" {
  description = "Nombre de la VPC"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
  default     = ""
}

variable "sg_name" {
  description = "Nombre del SG"
  type = string
  default = ""
}

variable "sg_rules" {
  description = "Reglas de entrada del SG"
  type        = list(map(string))
  default     = []
}
