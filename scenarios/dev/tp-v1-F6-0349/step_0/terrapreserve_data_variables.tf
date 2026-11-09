# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_aws_availability_zones_available" {
  description = "TerraPreserve D5-08: replaces data block aws_availability_zones/available"
  type = object({
    names = list(string)
  })
}
