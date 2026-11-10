# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_terraform_remote_state_eip" {
  description = "TerraPreserve D5-08: replaces data block terraform_remote_state/eip"
  type = object({
    outputs = object({
      public_ip_addr = string
    })
  })
}
