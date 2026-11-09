# --- Common ------------------------------------------------------------------
variable "name" {
  type        = string
  description = "The name of the worker."
}

# --- VPC ---------------------------------------------------------------------
variable "vpc_id" {
  type        = string
  description = "The ID of the VPC into which the worker instance is placed."
}

variable "subnet_id" {
  type        = string
  description = "The ID of the subnet into which the worker instance is placed."
}

# --- Bastion -----------------------------------------------------------------
variable "bastion_sg_id" {
  type        = string
  description = "The ID of the bastion Security Group."
}

# --- EC2 ---------------------------------------------------------------------
variable "ami_id" {
  type        = string
  description = "The ID of the worker instance AMI."
}

variable "instance_profile_name" {
  type        = string
  description = "The name of the instance profile attached to the worker instance."
}

variable "user_data_template" {
  type        = string
  description = "The template file used to generate user data injected into the worker instance."
}

variable "block_devices" {
  type = list(object({
    name        = string
    snapshot_id = string
    volume_size = number
  }))
  description = "A list of block devices attached to the worker instance."
  default     = []
}
