variable "cidr_block" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "name" {
  description = "The name tag for the VPC"
  type        = string
}

variable "subnet_count" {
  description = "Number of subnets to create"
  type        = number
  default     = 2
}

variable "subnet_size_override_list" {
  description = "Override for subnet size (CIDR block size, e.g., 24 for /24). If set, count is ignored and the list is used as a prefix."
  type        = list(number)
  default     = []
}

variable "env" {
    description = "The environment (e.g., tst, dev, acc, prd)"
    type        = string
    validation {
        condition     = contains(["tst", "dev", "acc", "prd"], var.env)
        error_message = "The env variable must be one of: tst, dev, acc, prd."
    }
}
