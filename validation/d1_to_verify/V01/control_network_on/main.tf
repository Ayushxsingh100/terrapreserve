# Control for the V01 network-block proof: the same unreachable proxy, but WITHOUT the skip_* flags.
# The provider then tries to validate the credentials (sts) over HTTPS, so the plan must fail with a
# proxy connection error. That shows the proxy variables are honoured by the provider; the V01 plan,
# which succeeded under the same variables, therefore made no HTTP request.

provider "aws" {
  region      = "us-east-1"
  max_retries = 1
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
