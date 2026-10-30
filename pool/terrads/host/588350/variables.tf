# Existing key pair
variable "key_name" {
    type        = string
    description = "Name of the existing key pair"
}

variable "instance_type" {  
    type        = string
}

variable "ami" {
    type        = string  
}

variable "volume_size" {
    type        = number
}

variable "volume_type" {
    type        = string
}