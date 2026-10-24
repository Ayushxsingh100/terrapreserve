terraform {
  required_version = "~> 1.15.0"
}

resource "terraform_data" "x" {
  count = 1
  input = "v"
}

moved {
  from = terraform_data.x["a"]
  to   = terraform_data.x[0]
}
