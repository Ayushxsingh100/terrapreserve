data "aws_ip_ranges" "ap_northeast" {
  regions  = ["ap-northeast-2"]
  services = ["ec2"]
}

resource "aws_security_group" "from_ap_northeast" {
  name = "from_ap_northeast"

  ingress {
    from_port   = "443"
    to_port     = "443"
    protocol    = "tcp"
    cidr_blocks = data.aws_ip_ranges.ap_northeast.cidr_blocks
  }
  tags = {
    CreateDate = data.aws_ip_ranges.ap_northeast.create_date
    SyncToken  = data.aws_ip_ranges.ap_northeast.sync_token
  }
}
