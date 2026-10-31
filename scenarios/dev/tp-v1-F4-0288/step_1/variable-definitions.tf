variable "aws_access_key_id" {
  description = "The access key ID for the AWS API"
  type        = string
}

variable "aws_secret_access_key" {
  description = "The access key secret for the AWS API"
  type        = string
  sensitive   = true
}

variable "ami_id" {
  description = "The ID of the desired image for the server"
  type        = string

  validation {
    condition     = length(var.ami_id) > 4 && substr(var.ami_id, 0, 4) == "ami-"
    error_message = "The `ami_id` value must be a valid AMI ID, starting with \"ami-\"."
  }
}

variable "keypair_name" {
  description = "The name of the keypair to add to an EC2 instance"
  type        = string
}
