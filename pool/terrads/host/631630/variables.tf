# Variable para el nombre del proyecto.
# Descripción: El nombre del proyecto.
variable "project_name" {
  description = "The name of the project"
  type        = string
}

# Variable para el entorno.
# Descripción: El entorno (dev/prod).
variable "environment" {
  description = "The environment (dev/prod)"
  type        = string
}

# Variable para el ID de la VPC.
# Descripción: El ID de la VPC donde se creará el grupo de seguridad.
variable "vpc_id" {
  description = "The ID of the VPC where the security group will be created"
  type        = string
}

