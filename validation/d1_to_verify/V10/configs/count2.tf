terraform {
  required_version = "~> 1.15.0"
}

resource "terraform_data" "x" {
  count = 2
  input = "v"
}
