locals {
  sgConfig = [
    for data in var.sgData : {
      name    = data.name
      ingress = data.ingress
    }
  ]
}

locals {
  security_groups = flatten(local.sgConfig)
}