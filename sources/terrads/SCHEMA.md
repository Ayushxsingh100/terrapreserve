# TerraDS database schema

Read from `TerraDS.sqlite` (opened read-only) by `sources/terrads/measure_yield.py`. Row counts are measured.

## table `Modules`: 394,004 rows

| Column | Declared type | Not null | Primary key |
|---|---|---|---|
| `Id` | `INTEGER` | yes | yes |
| `RepositoryId` | `INTEGER` | yes | no |
| `Path` | `TEXT` | yes | no |
| `Providers` | `TEXT` | yes | no |
| `ModuleCalls` | `TEXT` | yes | no |
| `DiagnosticMessages` | `TEXT` | no | no |

## table `Repositories`: 82,749 rows

| Column | Declared type | Not null | Primary key |
|---|---|---|---|
| `Id` | `INTEGER` | yes | yes |
| `Name` | `TEXT` | yes | no |
| `FullName` | `TEXT` | yes | no |
| `CreatedAt` | `TEXT` | yes | no |
| `Description` | `TEXT` | no | no |
| `License` | `TEXT` | no | no |
| `StarCount` | `INTEGER` | yes | no |
| `ForkCount` | `INTEGER` | yes | no |
| `HtmlUrl` | `TEXT` | yes | no |
| `GitUrl` | `TEXT` | yes | no |
| `SshUrl` | `TEXT` | yes | no |
| `CloneUrl` | `TEXT` | yes | no |
| `Homepage` | `TEXT` | no | no |
| `Archived` | `INTEGER` | yes | no |
| `Topics` | `TEXT` | yes | no |
| `LatestCommitAt` | `TEXT` | yes | no |
| `LatestCommitSha` | `TEXT` | yes | no |
| `SizeInKb` | `INTEGER` | yes | no |

## table `Resources`: 2,497,629 rows

| Column | Declared type | Not null | Primary key |
|---|---|---|---|
| `Id` | `INTEGER` | yes | yes |
| `ModuleId` | `INTEGER` | yes | no |
| `ResourceType` | `TEXT` | yes | no |
| `Name` | `TEXT` | yes | no |
| `Type` | `TEXT` | yes | no |
| `Provider` | `TEXT` | yes | no |

## table `sqlite_sequence`: 3 rows

| Column | Declared type | Not null | Primary key |
|---|---|---|---|
| `name` | `` | no | no |
| `seq` | `` | no | no |

## view `RedistributableRepositories`: 82,749 rows

| Column | Declared type | Not null | Primary key |
|---|---|---|---|
| `Id` | `INTEGER` | no | no |
| `Name` | `TEXT` | no | no |
| `FullName` | `TEXT` | no | no |
| `CreatedAt` | `TEXT` | no | no |
| `Description` | `TEXT` | no | no |
| `License` | `TEXT` | no | no |
| `StarCount` | `INTEGER` | no | no |
| `ForkCount` | `INTEGER` | no | no |
| `HtmlUrl` | `TEXT` | no | no |
| `GitUrl` | `TEXT` | no | no |
| `SshUrl` | `TEXT` | no | no |
| `CloneUrl` | `TEXT` | no | no |
| `Homepage` | `TEXT` | no | no |
| `Archived` | `INTEGER` | no | no |
| `Topics` | `TEXT` | no | no |
| `LatestCommitAt` | `TEXT` | no | no |
| `LatestCommitSha` | `TEXT` | no | no |
| `SizeInKb` | `INTEGER` | no | no |
