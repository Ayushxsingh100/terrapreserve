variable "availability_zones" {
  description = "Lista de zonas de disponibilidad a usar en la región"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "cdrs" {
  description = "cdrs a utilizar"
  type        = string
  default     = "0.0.0.0/0"
}