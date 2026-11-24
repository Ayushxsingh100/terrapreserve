variable "aws_region" {
  default = "us-west-1"
  type = string
}

variable env {
  description = "GovCloud deployment environment"
  type = string
  default = "govcloud-dev"
}