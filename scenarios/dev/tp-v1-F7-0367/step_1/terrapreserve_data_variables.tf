# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_aws_instance_bigip" {
  description = "TerraPreserve D5-08: replaces data block aws_instance/bigip"
  type = object({
    private_ip = string
    public_ip  = string
  })
}

variable "tp_ds_aws_instance_node_vm" {
  description = "TerraPreserve D5-08: replaces data block aws_instance/node_vm"
  type = object({
    public_ip = string
  })
}

variable "tp_ds_aws_security_group_selected" {
  description = "TerraPreserve D5-08: replaces data block aws_security_group/selected"
  type = object({
    id = string
  })
}
