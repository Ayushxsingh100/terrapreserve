data "aws_vpc" "default" {
  default = true
}

resource "aws_subnet" "this" {
  vpc_id     = data.aws_vpc.default.id
  cidr_block = "172.31.0.0/16"

  lifecycle {
    create_before_destroy = true
    postcondition {
      condition     = self.availability_zone == "us-central-1a"
      error_message = "Self - Invalid availability zone. Must be us-central-1a."
    }
  }
}