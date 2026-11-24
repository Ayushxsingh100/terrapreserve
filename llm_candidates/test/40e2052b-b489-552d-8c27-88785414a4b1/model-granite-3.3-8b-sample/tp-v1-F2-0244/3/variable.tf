variable "vpc_id" {}

variable "tags" {
  type = map
  default = {
    Name = "sum-ait-priv-subnet-1"
  }
}

variable "priv_cidr_block-1" {
  default = "11.0.20.0/24"
}
