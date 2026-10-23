terraform {
  required_version = "~> 1.15.0"
}

resource "terraform_data" "x" {
  for_each = toset(["a"])
  input    = "v"
}

moved {
  from = terraform_data.x
  to   = terraform_data.x["a"]
}
