
resource "aws_security_group" "from_ap_northeast" {
  name = "from_ap_northeast"

  ingress {
    from_port   = "443"
    to_port     = "443"
    protocol    = "tcp"
    cidr_blocks = var.tp_ds_aws_ip_ranges_ap_northeast.cidr_blocks
  }
  tags = {
    CreateDate = var.tp_ds_aws_ip_ranges_ap_northeast.create_date
    SyncToken  = var.tp_ds_aws_ip_ranges_ap_northeast.sync_token
  }
}
