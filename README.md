# DOMjudge CLI

A production-ready command-line tool for managing DOMjudge infrastructure and programming contests. Deploy, configure, and manage competitive programming platforms with Infrastructure-as-Code principles.

[![PyPI version](https://img.shields.io/pypi/v/domjudge-cli.svg)](https://pypi.org/project/domjudge-cli/)
[![Python Support](https://img.shields.io/pypi/pyversions/domjudge-cli.svg)](https://pypi.org/project/domjudge-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Important: Tool Scope](#important-tool-scope)
- [Command Reference](#command-reference)
  - [dom init](#dom-init)
  - [dom infra](#dom-infra)
  - [dom contest](#dom-contest)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- **Python**: 3.10 or higher
- **Docker**: Required for running DOMjudge infrastructure
- **Operating System**: Linux (Ubuntu 22.04 recommended), macOS

### System Requirements (Linux)

Enable **cgroups** for judgehost functionality:

**Ubuntu 22.04:**

1. Create GRUB configuration:
   ```bash
   sudo vi /etc/default/grub.d/99-domjudge-cgroups.cfg
   ```

2. Add this line:
   ```
   GRUB_CMDLINE_LINUX_DEFAULT="cgroup_enable=memory swapaccount=1 systemd.unified_cgroup_hierarchy=0"
   ```

3. Update and reboot:
   ```bash
   sudo update-grub
   sudo reboot
   ```

4. Verify:
   ```bash
   cat /proc/cmdline  # Should show cgroup settings
   ```

### Install

```bash
pip install domjudge-cli
dom --version
```

---

## Quick Start

```bash
# 1. Initialize configuration
dom init

# 2. Deploy infrastructure
dom infra apply

# 3. Create contests with problems and teams
dom contest apply
```

Access DOMjudge at `http://localhost:8080` (or configured port).

---

## ⚠ IMPORTANT: Tool Scope

This tool is designed for **INITIAL SETUP** of DOMjudge infrastructure and contests.

### What This Tool Does ✓

- Deploy DOMjudge infrastructure (Docker containers)
- Create new contests with problems and teams
- Plan changes before applying them
- Scale judgehost count

### What This Tool Does NOT Do ❌

- ❌ **Update existing contests** (DOMjudge API limitation)
- ❌ **Update team/problem data after creation**
- ❌ **Ongoing contest management** (use DOMjudge web UI instead)

**Example:**

```bash
# ✓ Initial setup - Works perfectly
dom init
dom infra apply
dom contest apply

# ❌ Updating existing contest - NOT supported
vim dom-judge.yaml  # Change contest duration
dom contest apply   # ⚠ Warning: Update manually in web UI
```

For ongoing management, use the DOMjudge web interface.

---

## Command Reference

### Global Options

All commands support:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable detailed logging |
| `--no-color` | Disable colored output |
| `--version`, `-v` | Show version |
| `--help` | Show help |

**Example:**
```bash
dom --verbose infra status
```

---

### dom init

Initialize DOMjudge configuration file.

```bash
dom init [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--overwrite` | Overwrite existing configuration |
| `--dry-run` | Preview without creating files |

#### Usage

Launches an interactive wizard to create `dom-judge.yaml` with:
- Infrastructure settings (port, judges)
- Contest details
- Problems and teams

**Examples:**

```bash
# Basic initialization
dom init

# Preview what would be created
dom init --dry-run

# Overwrite existing config
dom init --overwrite
```

---

### dom infra

Manage DOMjudge infrastructure.

#### Commands

- [`dom infra apply`](#dom-infra-apply) - Deploy infrastructure
- [`dom infra plan`](#dom-infra-plan) - Preview infrastructure changes
- [`dom infra status`](#dom-infra-status) - Check infrastructure health
- [`dom infra destroy`](#dom-infra-destroy) - Remove infrastructure

---

#### dom infra apply

Deploy or update infrastructure from configuration.

```bash
dom infra apply [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |
| `--dry-run` | Preview without applying |

**Usage:**

Deploys Docker containers for:
- DOMserver (web interface + API)
- MariaDB database
- Judgehosts (configurable count)
- MySQL client

**Examples:**

```bash
# Deploy with default config
dom infra apply

# Use custom config file
dom infra apply -f my-config.yaml

# Preview deployment
dom infra apply --dry-run

# Deploy with verbose logging
dom infra apply --verbose
```

**Access:** After deployment, DOMjudge is available at configured port (default: `http://localhost:8080`)

---

#### dom infra plan

Show infrastructure changes before applying.

```bash
dom infra plan [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |

**Usage:**

Analyzes configuration and displays:
- Whether infrastructure needs creation or updates
- Safe changes (e.g., scaling judges) vs. changes requiring restart
- Current vs. desired state comparison

**Examples:**

```bash
# Preview infrastructure changes
dom infra plan

# Use custom config
dom infra plan -f my-config.yaml
```

**Output shows:**
- Port changes (requires restart)
- Judge count changes (safe live update)
- Password changes (requires restart)

---

#### dom infra status

Check infrastructure health.

```bash
dom infra status [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file for expected state |
| `--json` | Output as JSON |

**Usage:**

Checks status of:
- Docker daemon
- DOMserver container
- MariaDB database
- Judgehost containers
- MySQL client
- Network connectivity

**Examples:**

```bash
# Check status
dom infra status

# Check against expected config
dom infra status -f dom-judge.yaml

# JSON output for scripts
dom infra status --json
```

**Exit codes:**
- `0` - All healthy
- `1` - Issues detected

---

#### dom infra destroy

Remove all infrastructure.

```bash
dom infra destroy [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--confirm` | **Required** - Confirm destruction |
| `--force-delete-volumes` | Delete data volumes (PERMANENT) |
| `--dry-run` | Preview without destroying |

**Usage:**

Stops and removes containers. **By default, preserves volumes** (contest data, submissions, database).

**Examples:**

```bash
# Remove infrastructure (keep data)
dom infra destroy --confirm

# Complete removal (DATA LOSS)
dom infra destroy --confirm --force-delete-volumes

# Preview what would be removed
dom infra destroy --dry-run
```

**Safety:** Requires `--confirm` flag to prevent accidents.

---

### dom contest

Manage contests, problems, and teams.

#### Commands

- [`dom contest apply`](#dom-contest-apply) - Create contests
- [`dom contest plan`](#dom-contest-plan) - Preview contest changes
- [`dom contest verify-problemset`](#dom-contest-verify-problemset) - Verify problems
- [`dom contest inspect`](#dom-contest-inspect) - Inspect configuration

---

#### dom contest apply

Create contests with problems and teams.

```bash
dom contest apply [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |
| `--dry-run` | Preview without applying |

**Usage:**

Creates or updates:
- Contests
- Problem packages
- Teams and affiliations
- Contest settings

**Important:** Cannot update existing contest fields (API limitation). For changes after creation, use DOMjudge web UI.

**Examples:**

```bash
# Create contests from config
dom contest apply

# Use custom config
dom contest apply -f my-contest.yaml

# Preview changes
dom contest apply --dry-run

# Verbose output
dom contest apply --verbose
```

---

#### dom contest plan

Show contest changes before applying.

```bash
dom contest plan [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |

**Usage:**

Analyzes configuration and displays:
- Contests to be created
- Field changes detected (with warnings if not updatable)
- Problems/teams to be added
- Current vs. desired state

**Examples:**

```bash
# Preview contest changes
dom contest plan

# Use custom config
dom contest plan -f my-config.yaml
```

**Output shows:**
- New contests to create
- Existing contests and detected changes
- Problems/teams to add
- Warnings for unsupported updates

---

#### dom contest verify-problemset

Verify problems by running test submissions.

```bash
dom contest verify-problemset CONTEST_NAME [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `CONTEST_NAME` | Contest name or shortname |

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |
| `--dry-run` | Preview without running |

**Usage:**

Validates problems by:
- Running sample submissions
- Checking expected results
- Verifying performance limits
- Reporting successes/failures

**Examples:**

```bash
# Verify contest problemset
dom contest verify-problemset "ICPC Regional 2025"

# Use shortname
dom contest verify-problemset SAMPLE2025

# With custom config
dom contest verify-problemset SAMPLE2025 -f config.yaml

# Preview what would be verified
dom contest verify-problemset SAMPLE2025 --dry-run
```

**Exit codes:**
- `0` - All problems verified
- `1` - Verification failed

---

#### dom contest inspect

Inspect loaded configuration.

```bash
dom contest inspect [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-f`, `--file PATH` | Config file (default: `dom-judge.yaml`) |
| `--format EXPR` | JMESPath expression for filtering |
| `--show-secrets` | Show secret values (default: masked) |

**Usage:**

Displays parsed configuration with validation.

**Examples:**

```bash
# Inspect configuration
dom contest inspect

# Show with secrets
dom contest inspect --show-secrets

# Filter specific data
dom contest inspect --format "contests[0].name"

# Use custom config
dom contest inspect -f my-config.yaml
```

---

## Configuration

Configuration is defined in `dom-judge.yaml` (created by `dom init`).

### File Structure

```yaml
infra:
  port: 8080
  judges: 4
  password: "your-secure-password"

contests:
  - name: "ICPC Regional 2025"
    shortname: "ICPC2025"
    duration: "5:00:00"
    problems:
      - archive: "problems/hello/"
        platform: "domjudge"
        color: "blue"
      - archive: "problems/fizzbuzz.zip"
        platform: "domjudge"
        color: "red"
      - archive: "problems/polygon-problem-linux.zip"
        platform: "polygon"
        color: "green"
        with_statement: true
    teams:
      - name: "Team Alpha"
        affiliation: "University A"
        country: "USA"
      - name: "Team Beta"
        affiliation: "University B"
        country: "CAN"
```

### Infrastructure Section

| Field | Type | Description |
|-------|------|-------------|
| `port` | integer | DOMjudge web port (1024-65535) |
| `judges` | integer | Number of judgehost containers |
| `password` | string | Admin password (8-128 chars) |

### Contest Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Contest display name |
| `shortname` | string | Yes | Short identifier (3-32 chars) |
| `duration` | string | Yes | Format: `H:MM:SS` |
| `formal_name` | string | No | Official name |
| `start_time` | datetime | No | ISO 8601 format |
| `penalty_time` | integer | No | Minutes per wrong submission |
| `problems` | list | Yes | Problem packages |
| `teams` | list | Yes | Team registrations |

### Problem Package

The tool supports **two problem formats**:

1. **DOMjudge/Kattis Problem Package Format** (recommended)
2. **Polygon Format** (automatically converted to DOMjudge format)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `archive` | string | Yes | Path to problem archive (.zip) or directory |
| `platform` | string | Yes | `"domjudge"` or `"polygon"` |
| `color` | string | Yes | Problem color (hex code or name) |
| `with_statement` | boolean | No | Include problem statement (Polygon only, default: `true`) |

**DOMjudge/Kattis Format - Required files:**
- `problem.yaml` - Problem metadata
- `domjudge-problem.ini` - DOMjudge settings
- `data/sample/*.in` - Sample inputs
- `data/sample/*.ans` - Sample outputs
- `data/secret/*.in` - Test cases
- `data/secret/*.ans` - Expected outputs

**Polygon Format:**
- `.zip` archive from Codeforces Polygon
- **Important:** Export as **Linux package** (not Standard or Windows)
- Automatically converted to DOMjudge format during import

**Example configuration:**
```yaml
problems:
  # DOMjudge format (directory)
  - archive: "problems/hello/"
    platform: "domjudge"
    color: "#FF5733"
  
  # DOMjudge format (zip)
  - archive: "problems/fizzbuzz.zip"
    platform: "domjudge"
    color: "blue"
  
  # Polygon format (must be Linux package!)
  - archive: "problems/polygon-problem-linux.zip"
    platform: "polygon"
    color: "green"
    with_statement: true
```

#### Problem Configuration Patterns

The tool supports multiple ways to specify problem configurations:

**1. Inline problems (as shown above)**
```yaml
contests:
  - name: "Contest 1"
    problems:
      - archive: "problems/hello/"
        platform: "domjudge"
        color: "blue"
```

**2. External problems file**
```yaml
contests:
  - name: "Contest 1"
    problems:
      from: "problems.yaml"  # or problems.yml
```

Then create `problems.yaml`:
```yaml
- archive: "problems/hello/"
  platform: "domjudge"
  color: "blue"
- archive: "problems/fizzbuzz.zip"
  platform: "domjudge"
  color: "red"
```

**3. Problems from a directory**
```yaml
contests:
  - name: "Contest 1"
    problems:
      from: "contest1-problems/"
```

The tool will look for `contest1-problems/problems.yaml` or `contest1-problems/problems.yml`.

**4. Default problems lookup**
```yaml
contests:
  - name: "Contest 1"
    problems: {}  # Empty object triggers default lookup
```

The tool will automatically look for `problems.yaml` or `problems.yml` in the same directory as `dom-judge.yaml`.

This pattern is useful when:
- You want to keep your main config file clean and focused
- Multiple contests share the same problem set
- You're managing a large problem set separately

### Team Registration

Teams can be defined in two ways: inline YAML or CSV file import.

#### Inline YAML Format

Define teams directly in your configuration file:

```yaml
teams:
  - name: "Team Alpha"
    affiliation: "University A"
    country: "USA"
  - name: "Team Beta"
    affiliation: "University B"
    country: "CAN"
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Team display name |
| `affiliation` | string | Yes | Organization name |
| `country` | string | Yes | 3-letter code (USA, CAN, etc.) |

#### CSV File Format

For contests with many teams, import from CSV files:

```yaml
teams:
  from: "teams.csv"
  delimiter: ","
  rows: "2-50"
  name: "$2"
  affiliation: "$3"
  country: "$4"
```

**Configuration Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | Yes | Path to CSV/TSV file |
| `delimiter` | string | No | Field separator (`,` for CSV, `\t` for TSV) |
| `rows` | string | Yes | Row range to import (e.g., `"2-50"`) |
| `name` | string | Yes | Column mapping for team name (e.g., `"$2"`) |
| `affiliation` | string | Yes | Column mapping for affiliation (e.g., `"$3"`) |
| `country` | string | Yes | Column mapping for country code (e.g., `"$4"`) |

**Interactive Column Mapping:**

When you run `dom init`, you'll:
1. Select your teams CSV file
2. See a preview of the first few rows with column numbers
3. Choose which columns map to name, affiliation, and country
4. Confirm or adjust the detected row range

This ensures flexibility regardless of your CSV structure.

**CSV File Best Practices:**

1. **Include clear headers** in the first row (excluded from import)
2. **Use UTF-8 encoding** to support international characters
3. **Keep consistent formatting** across all rows
4. **Include all required fields**: name, affiliation, country

**Example CSV: teams.csv**

```csv
id,name,affiliation,country
1,Team Alpha,University A,USA
2,Team Beta,University B,CAN
3,Team Gamma,College C,FRA
4,Team Delta,Institute D,DEU
5,Team Epsilon,Academy E,GBR
```

**Alternative CSV (different column order):**

```csv
team_name,country_code,university,team_id
Alpha Warriors,USA,MIT,T001
Beta Coders,CAN,UBC,T002
Gamma Hackers,FRA,ENS,T003
```

During `dom init`, you'll map:
- Column 1 (`team_name`) → name: `"$1"`
- Column 3 (`university`) → affiliation: `"$3"`
- Column 2 (`country_code`) → country: `"$2"`

**Country Codes:**

Use ISO 3166-1 alpha-3 country codes. Common examples:

| Code | Country |
|------|---------|
| USA | United States |
| CAN | Canada |
| DEU | Germany |
| GBR | United Kingdom |
| JPN | Japan |
| MAR | Morocco |


**Row Range Specification:**

The `rows` field defines which rows contain team data:

- Format: `"start-end"` (1-indexed, inclusive)
- Example: `"2-50"` imports rows 2 through 50
- Row 1 is typically headers (excluded)
- During `dom init`, the tool auto-detects the range based on file size

**TSV Format Support:**

For tab-separated files, use `.tsv` extension:

```yaml
teams:
  from: "teams.tsv"
  delimiter: "\t"  # Tab character
  rows: "2-100"
  name: "$1"
  affiliation: "$2"
  country: "$3"
```

**Complete Example:**

```yaml
contests:
  - name: "ICPC Regional 2025"
    shortname: "ICPC2025"
    duration: "5:00:00"
    
    problems:
      from: "problems.yaml"
    
    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-45"
      name: "$2"
      affiliation: "$3"
      country: "$4"
```

---

## Usage Examples

### Complete Setup Workflow

```bash
# 1. Create configuration
dom init

# 2. Review infrastructure plan
dom infra plan

# 3. Deploy infrastructure
dom infra apply

# 4. Verify deployment
dom infra status

# 5. Review contest plan
dom contest plan

# 6. Create contests
dom contest apply

# 7. Verify problems
dom contest verify-problemset "My Contest"
```

### Scaling Judgehosts

```bash
# Edit config to change judge count
vim dom-judge.yaml  # Change judges: 4 -> 8

# Preview changes
dom infra plan  # Shows: Safe judge scaling

# Apply changes (no downtime)
dom infra apply
```

### Complete Teardown

```bash
# Remove infrastructure (keep data)
dom infra destroy --confirm

# Complete removal including data
dom infra destroy --confirm --force-delete-volumes
```

### Health Check Script

```bash
#!/bin/bash
# Check if DOMjudge is healthy

if dom infra status --json > /dev/null 2>&1; then
  echo "✓ DOMjudge is healthy"
  exit 0
else
  echo "✗ DOMjudge has issues"
  exit 1
fi
```

### Multiple Environments

```bash
# Production
dom infra apply -f production.yaml
dom contest apply -f production.yaml

# Staging
dom infra apply -f staging.yaml
dom contest apply -f staging.yaml
```

---

## Troubleshooting

### Infrastructure Issues

**Problem:** Containers won't start

```bash
# Check Docker daemon
docker ps

# Check logs
docker logs domjudge-cli-domserver

# Verify cgroups (Linux)
cat /proc/cmdline
```

**Problem:** Port already in use

```bash
# Change port in config
vim dom-judge.yaml  # Change port: 8080 -> 9090

# Destroy and redeploy
dom infra destroy --confirm
dom infra apply
```

**Problem:** Judgehosts not running

```bash
# Check status
dom infra status

# View logs
docker logs domjudge-cli-judgehost-1

# Verify cgroups configuration
```

### Contest Issues

**Problem:** Problems fail to upload

```bash
# Verify problem package format
# Must have problem.yaml and data/ directory

# Check logs
dom contest apply --verbose
```

**Problem:** Team creation fails

```bash
# Check team data format
# Name, affiliation, country required

# Use verbose mode
dom contest apply --verbose
```

**Problem:** "Contest already exists" warning

This is expected when trying to update contest fields. The tool can only CREATE contests, not update them. Use DOMjudge web UI for updates.

### General Issues

**Problem:** Configuration validation fails

```bash
# Inspect parsed config
dom contest inspect

# Check YAML syntax
# Ensure proper indentation and structure
```

**Problem:** Docker permission denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

---

## Best Practices

1. **Use version control** for configuration files
2. **Test with `--dry-run`** before applying changes
3. **Use `plan` commands** to preview changes
4. **Keep credentials secure** - use environment variables or secrets manager
5. **Back up volumes** before using `--force-delete-volumes`
6. **Monitor with `infra status`** in production
7. **Use DOMjudge web UI** for contest management after initial setup

---

## Resources

- **Documentation:** https://github.com/AnasImloul/domjudge-cli
- **Issues:** https://github.com/AnasImloul/domjudge-cli/issues
- **DOMjudge:** https://www.domjudge.org/
- **Kattis Problem Format:** https://www.kattis.com/problem-package-format/

---

**Built with ❤️ for the competitive programming community.**
