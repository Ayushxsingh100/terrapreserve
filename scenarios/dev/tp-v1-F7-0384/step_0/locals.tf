locals {

  identifier = "dev"

  vpc_cidr               = "10.10.0.0/18"
  vpc_enable_dns         = true
  vpc_instance_tenancy   = "default"
  vpc_network_monitoring = true

  availability_zones = [
    "ap-southeast-1a",
    "ap-southeast-1b",
  ]

  subnet_cidr = cidrsubnets(
    local.vpc_cidr,
    4, 4, # public
    4, 4, # data
    3, 3, # app
  )

  nat_ami_owner      = "568608671756"
  nat_ami_arch       = "arm64"
  nat_ami_name       = "fck-nat-amzn2-hvm-1.2.1-*"
  nat_instance_type  = "t4g.nano"
  nat_max_spot_price = 0.004

}
