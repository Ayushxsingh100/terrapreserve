# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_aws_availability_zones_working" {
  description = "TerraPreserve D5-08: replaces data block aws_availability_zones/working"
  type = object({
    names = list(string)
  })
}

variable "tp_ds_aws_caller_identity_current" {
  description = "TerraPreserve D5-08: replaces data block aws_caller_identity/current"
  type = object({
    account_id = string
  })
}

variable "tp_ds_aws_region_current" {
  description = "TerraPreserve D5-08: replaces data block aws_region/current"
  type = object({
    description = string
    name        = string
  })
}

variable "tp_ds_aws_vpc_prod_vpc" {
  description = "TerraPreserve D5-08: replaces data block aws_vpc/prod_vpc"
  type = object({
    cidr_block = string
    id         = string
  })
}

variable "tp_ds_aws_vpcs_my_vpcs" {
  description = "TerraPreserve D5-08: replaces data block aws_vpcs/my_vpcs"
  type = object({
    ids = list(string)
  })
}
