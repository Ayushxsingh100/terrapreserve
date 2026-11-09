"""D5a Step 4: the error classifier of ``tools/run_d5a_feasibility.py`` on synthetic Terraform output.

Classes (work package Step 4): data source needs API; provider tried to call AWS; variable error; other.
The fixtures are shaped like Terraform 1.15 diagnostics; no AWS endpoint is contacted.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from run_d5a_feasibility import classify  # noqa: E402

AZ = """
Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: refused.

  with data.aws_availability_zones.available,
  on main.tf line 5, in data "aws_availability_zones" "available":
   5: data "aws_availability_zones" "available" {}
"""
RESOURCE_CALL = """
Error: reading something: operation error STS: GetCallerIdentity, https response error StatusCode: 0, request send failed, proxyconnect tcp: dial tcp 127.0.0.1:9

  with aws_iam_role.r,
  on main.tf line 1, in resource "aws_iam_role" "r":
"""
NO_VALUE = """
Error: No value for required variable

  on variables.tf line 1:
   1: variable "vpc_config" {
"""
CIDR = """
Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder

  with aws_subnet.s,
  on main.tf line 3, in resource "aws_subnet" "s":
   3:   cidr_block = var.cidr_block
"""
FUNC = """
Error: Error in function call

  on main.tf line 9, in resource "aws_subnet" "s":
   9:   cidr_block = cidrsubnet(var.vpc_cidr, 8, 1)
    ├────────────────
    │ while calling cidrsubnet(prefix, newbits, netnum)
    │ var.vpc_cidr is "tp-placeholder"

Call to function "cidrsubnet" failed: invalid CIDR expression.
"""
OTHER = """
Error: Unsupported argument

  on main.tf line 2, in resource "aws_instance" "x":
   2:   foo = 1
"""


REMOTE_STATE = """
data.terraform_remote_state.eip: Reading...

Error: No valid credential sources found

Please see https://developer.hashicorp.com/terraform/language/backend/s3
"""
DEFAULT_CIDR = """
Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:

  with aws_vpc.vpc,
  on main.tf line 7, in resource "aws_vpc" "vpc":
   7:   cidr_block           = var.network_address_space
"""


VV2_LITERAL = """
Error: "tp-alt" is not a valid CIDR block: invalid CIDR address: tp-alt

  with aws_subnet.s,
  on main.tf line 3, in resource "aws_subnet" "s":
"""


class TestClassify(unittest.TestCase):
    def test_vv2_value_in_the_message(self) -> None:
        self.assertEqual(classify(VV2_LITERAL)[:2],
                         ("variable error", "vv-2 value rejected in an expression or by the provider"))

    def test_remote_state_credential_lookup_is_a_data_source(self) -> None:
        cls, cause, _ = classify(REMOTE_STATE, set())
        self.assertEqual(cls, "data source needs API")
        self.assertTrue(cause.startswith("terraform_remote_state: AWS credential lookup failed"))

    def test_located_error_is_not_blamed_on_an_earlier_data_read(self) -> None:
        text = "data.aws_region.current: Reading...\n" + FUNC
        self.assertEqual(classify(text, {"vpc_cidr"})[0], "variable error")

    def test_declared_default_versus_vv1_value(self) -> None:
        self.assertEqual(classify(DEFAULT_CIDR, {"tp_db_password"})[:2],
                         ("variable error",
                          "a declared default (not set by vv-2) rejected in an expression or by the provider"))
        self.assertEqual(classify(DEFAULT_CIDR, {"network_address_space"})[1],
                         "vv-2 value rejected in an expression or by the provider")

    def test_data_source(self) -> None:
        cls, cause, first = classify(AZ)
        self.assertEqual(cls, "data source needs API")
        self.assertEqual(cause, "aws_availability_zones: AWS request refused")
        self.assertTrue(first.startswith("Error: fetching Availability Zones"))

    def test_provider_call_outside_data(self) -> None:
        self.assertEqual(classify(RESOURCE_CALL)[0], "provider tried to call AWS")

    def test_variable_errors(self) -> None:
        self.assertEqual(classify(NO_VALUE)[:2], ("variable error", "unresolved variable has no value"))
        self.assertEqual(classify(CIDR)[0], "variable error")
        self.assertEqual(classify(FUNC)[0], "variable error")

    def test_other(self) -> None:
        self.assertEqual(classify(OTHER)[0], "other")
        self.assertEqual(classify("")[0], "other")

    def test_first_error_wins(self) -> None:
        self.assertEqual(classify(OTHER + AZ)[0], "other")
        self.assertEqual(classify(AZ + OTHER)[0], "data source needs API")


if __name__ == "__main__":
    unittest.main()
