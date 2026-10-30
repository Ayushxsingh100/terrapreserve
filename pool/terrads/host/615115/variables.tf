variable "vpc_cidr" {
  description = "CIDR block da VPC"
  type        = string
}

variable "public_subnet_cidr_az1" {
  type        = string
  description = "CIDR block para a subnet pública na AZ 1"
  default     = "10.0.1.0/24"
}

variable "public_subnet_cidr_az2" {
  type        = string
  description = "CIDR block para a subnet pública na AZ 2"
  default     = "10.0.2.0/24"
}

variable "availability_zone" {
  type        = string
  description = "Zona de disponibilidade (será usado apenas para a instância, o LB precisa de múltiplas)"
  default     = "us-east-1a" 
}

variable "region" {
  type        = string
  description = "Região da AWS"
  default     = "us-east-1" 
}

variable "vpc_name" {
  description = "Nome da VPC e dos recursos de rede"
  type        = string
}
