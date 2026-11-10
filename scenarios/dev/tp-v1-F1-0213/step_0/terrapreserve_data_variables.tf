# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_aws_ip_ranges_ap_northeast" {
  description = "TerraPreserve D5-08: replaces data block aws_ip_ranges/ap_northeast"
  type = object({
    cidr_blocks = list(string)
    create_date = string
    sync_token  = string
  })
}
