# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the
# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).

variable "tp_ds_aws_availability_zones_available" {
  description = "TerraPreserve D5-08: replaces data block aws_availability_zones/available"
  type = object({
    names = list(string)
  })
}

variable "tp_ds_aws_ec2_transit_gateway_wan" {
  description = "TerraPreserve D5-08: replaces data block aws_ec2_transit_gateway/wan"
  type        = list(object({}))
}

variable "tp_ds_aws_ec2_transit_gateway_route_table_rt_service_vpc_attach" {
  description = "TerraPreserve D5-08: replaces data block aws_ec2_transit_gateway_route_table/rt_service_vpc_attach"
  type        = list(object({}))
}

variable "tp_ds_aws_ec2_transit_gateway_vpc_attachment_wan_att_service_vpc" {
  description = "TerraPreserve D5-08: replaces data block aws_ec2_transit_gateway_vpc_attachment/wan_att_service_vpc"
  type        = list(object({}))
}

variable "tp_ds_aws_subnet_wan_subnet" {
  description = "TerraPreserve D5-08: replaces data block aws_subnet/wan_subnet"
  type        = list(object({}))
}
