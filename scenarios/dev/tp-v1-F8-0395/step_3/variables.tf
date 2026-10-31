variable "ami_id" {
  description = "The AMI ID of the instance"
  type        = string
}

variable "vpc_id" {
  description = "AWS VPC"
  type        = string
}

variable "instance_type" {
  description = "The type of the instance"
  type        = string
}

variable "volume_size" {
  description = "The size of the root volume in GB"
  type        = number
}


variable "subnet_id" {
  description = "The VPC default subnet ID"
  type        = string
}

variable "ssh_key" {
  description = "AWS SSH key for accessing instances"
  type        = string
}

variable "ssh_key_path" {
  description = "private key path in the SSH client filesystem"
  type        = string
}

variable "ssh_user" {
  description = "SSH user the SSH client will connect as"
  type = string
}


variable "one_ee" {
  description = "Set to --enterprise <ee_token> for an EE setup or emtpy for CE"
  type        = string
}

variable "one_password" {
  description = "Password for the oneadmin user of the OpenNebula instance running on the minione AWS instance"
  type        = string
}

variable "one_sunstone_port" {
  description = "HTTP port where OpenNebula Sunstone will be running"
  type        = number
}

variable "one_fireedge_port" {
  description = "HTTP port where OpenNebula Sunstone will be running"
  type        = number
}

variable "one_version" {
  description = "OpenNebula version to install"
  type        = string
}
