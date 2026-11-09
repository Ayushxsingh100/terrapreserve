variable "ec2_ami" {}
variable "snapshot_id" { default = null }
variable "key" {}
variable "protect_enable" {}
variable "bat_count" { type = number }
variable "bat_type" {}
variable "bat_tag" {}
variable "azs" {}

variable "vpc_id" {}
variable "admin_sg" {}
variable "web_sg" {}