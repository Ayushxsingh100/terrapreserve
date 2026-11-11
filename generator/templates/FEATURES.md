# Controlled template features (generated)

Generated from `generator/templates/__init__.py` (tpl-v2.0) by `tools/make_template_features.py`; do not edit by hand. The eight columns after the id are the D4c-03 variation axes (see the module docstring for their values); the last three are further parameters, not axes.

Templates: 33. Minimum pairwise distance over the eight axes: 2.

| Template | sg_style | naming | subnets | routing | files | values | extras | egress | db subnets | instance | db class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tpl-01 | all_separate | standard | one_app | shared_public | single | literal | none | all | 2 | t3.micro | db.t3.micro |
| tpl-02 | all_inline | kebab | one_app | private_db | single | literal | none | all | 2 | t3.small | db.t3.small |
| tpl-03 | app_inline_db_separate | tier | db_count | shared_public | single | literal | none | all | 3 | t3.nano | db.t3.micro |
| tpl-04 | app_separate_db_inline | standard | one_app | private_db | single | literal | second_app_sg | all | 2 | t3.micro | db.t3.medium |
| tpl-05 | all_separate | component | one_app | shared_public | single | literal | second_app_sg | all | 3 | t3.small | db.t3.micro |
| tpl-06 | all_inline | env | db_count | private_db | single | literal | none | all | 3 | t3.medium | db.t3.small |
| tpl-07 | app_inline_db_separate | kebab | one_app | private_db | single | literal | second_app_sg | all | 2 | t3.micro | db.t3.micro |
| tpl-08 | app_separate_db_inline | standard | one_app | shared_public | split | literal | none | all | 3 | t3.nano | db.t3.micro |
| tpl-09 | all_separate | tier | db_count | private_db | single | literal | none | all | 2 | t3.small | db.t3.small |
| tpl-10 | all_inline | component | one_app | shared_public | single | locals | second_app_sg | all | 2 | t3.micro | db.t3.nano |
| tpl-11 | all_separate | prefixed | two_app | per_subnet | single | variables | none | all | 2 | t3.micro | db.t3.micro |
| tpl-12 | all_inline | short | one_app | private_db | split | locals | unattached_sg | all | 3 | t3.small | db.t3.small |
| tpl-13 | app_inline_db_separate | role | two_app | shared_public | single | literal | extra_subnet | db_only | 2 | t3.nano | db.t3.micro |
| tpl-14 | app_separate_db_inline | prefixed | db_count | per_subnet | split | literal | none | db_only | 2 | t3.medium | db.t3.small |
| tpl-15 | all_separate | short | db_count | private_db | single | locals | extra_subnet | db_only | 3 | t3.micro | db.t3.micro |
| tpl-16 | all_inline | role | db_count | per_subnet | single | variables | second_app_sg | all | 2 | t3.small | db.t3.micro |
| tpl-17 | app_inline_db_separate | standard | one_app | per_subnet | split | variables | unattached_sg | all | 3 | t3.micro | db.t3.small |
| tpl-18 | app_separate_db_inline | kebab | two_app | private_db | single | locals | none | all | 2 | t3.nano | db.t3.micro |
| tpl-19 | all_separate | tier | two_app | shared_public | split | literal | unattached_sg | db_only | 3 | t3.small | db.t3.medium |
| tpl-20 | all_inline | prefixed | two_app | shared_public | single | literal | extra_subnet | all | 2 | t3.micro | db.t3.micro |
| tpl-21 | app_inline_db_separate | component | db_count | private_db | single | variables | none | db_only | 3 | t3.medium | db.t3.micro |
| tpl-22 | app_separate_db_inline | env | one_app | shared_public | single | variables | extra_subnet | all | 2 | t3.small | db.t3.small |
| tpl-23 | all_separate | kebab | db_count | per_subnet | single | literal | extra_subnet | all | 2 | t3.nano | db.t3.micro |
| tpl-24 | all_inline | tier | one_app | per_subnet | split | literal | none | all | 3 | t3.micro | db.t3.small |
| tpl-25 | app_inline_db_separate | short | two_app | per_subnet | single | literal | second_app_sg | all | 2 | t3.small | db.t3.micro |
| tpl-26 | app_separate_db_inline | role | one_app | private_db | split | literal | second_app_sg | db_only | 3 | t3.micro | db.t3.micro |
| tpl-27 | all_separate | env | two_app | private_db | split | variables | none | all | 2 | t3.medium | db.t3.small |
| tpl-28 | all_inline | standard | two_app | private_db | single | locals | unattached_sg | all | 3 | t3.nano | db.t3.micro |
| tpl-29 | app_inline_db_separate | prefixed | one_app | shared_public | single | locals | none | all | 2 | t3.small | db.t3.medium |
| tpl-30 | app_separate_db_inline | short | db_count | shared_public | split | variables | unattached_sg | all | 2 | t3.micro | db.t3.micro |
| tpl-31 | all_separate | role | one_app | shared_public | single | locals | unattached_sg | db_only | 3 | t3.small | db.t3.small |
| tpl-32 | all_inline | kebab | db_count | shared_public | split | variables | extra_subnet | all | 3 | t3.micro | db.t3.micro |
| tpl-33 | app_inline_db_separate | env | db_count | per_subnet | split | locals | extra_subnet | db_only | 2 | t3.nano | db.t3.small |

## Per-cell operator coverage (D4c-04)

Number of operators of each family x class cell (s = safe, u = unsafe) that the template accepts (an operator that raises `OperatorNotApplicable` on the template's step 0 is not counted). A template with 0 in a cell does not serve that cell and is never assigned to it.

| Template | F1s | F1u | F2s | F2u | F3s | F3u | F4s | F4u | F5s | F5u | F6s | F6u | F7s | F7u | F8s | F8u |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tpl-01 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-02 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-03 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-04 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-05 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-06 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-07 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-08 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-09 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-10 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-11 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-12 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-13 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-14 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 4 | 1 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-15 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-16 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-17 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-18 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-19 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-20 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-21 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-22 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-23 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-24 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-25 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-26 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 4 | 1 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-27 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-28 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-29 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 6 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-30 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-31 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |
| tpl-32 | 3 | 3 | 3 | 3 | 5 | 3 | 3 | 3 | 4 | 1 | 3 | 3 | 4 | 3 | 3 | 3 |
| tpl-33 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 6 | 3 | 3 | 3 | 2 | 1 | 3 | 2 |

Templates that do not serve a cell: none.
