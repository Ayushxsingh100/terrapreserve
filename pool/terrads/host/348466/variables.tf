variable "instance_count" {
  default = 0
}

variable "key_name" {
  description = "Private key name to use with instance"
  default     = "Punk_ath"
}

variable "instance_type" {
  description = "AWS instance type"
  default     = "t2.micro"
}

variable "ami" {
  description = "Base AMI to launch the instances"

  # Bitnami NGINX AMI
  default = "ami-0b6fd73535e4b992b"
}
