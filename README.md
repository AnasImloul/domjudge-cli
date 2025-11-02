# DOMjudge CLI

A production-ready command-line tool for managing DOMjudge infrastructure and programming contests. Deploy, configure, and manage competitive programming platforms with Infrastructure-as-Code principles.

[![PyPI version](https://img.shields.io/pypi/v/domjudge-cli.svg)](https://pypi.org/project/domjudge-cli/)
[![Python Support](https://img.shields.io/pypi/pyversions/domjudge-cli.svg)](https://pypi.org/project/domjudge-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [System Requirements](#system-requirements)
  - [Quick Install](#quick-install)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
  - [dom init](#dom-init)
  - [dom infra](#dom-infra)
  - [dom contest](#dom-contest)
- [Configuration](#configuration)
  - [Configuration File Structure](#configuration-file-structure)
  - [Infrastructure Configuration](#infrastructure-configuration)
  - [Contest Configuration](#contest-configuration)
  - [Problem Configuration](#problem-configuration)
  - [Team Configuration](#team-configuration)
- [Usage Examples](#usage-examples)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Installation

### Prerequisites

- **Python**: 3.10 or higher
- **Docker**: Required for infrastructure management
- **Operating System**: Ubuntu 22.04 (recommended), macOS (limited support)

### System Requirements

Before installing the CLI, you must enable **cgroups** on Linux systems to ensure proper judgehost functionality.

**Ubuntu 22.04 Setup:**

1. Create or edit the GRUB configuration:
   ```bash
   sudo vi /etc/default/grub.d/99-domjudge-cgroups.cfg
   ```

2. Add the following line:
   ```
   GRUB_CMDLINE_LINUX_DEFAULT="cgroup_enable=memory swapaccount=1 systemd.unified_cgroup_hierarchy=0"
   ```

3. Update GRUB and reboot:
   ```bash
   sudo update-grub
   sudo reboot
   ```

**Verify cgroups are enabled:**
```bash
cat /proc/cmdline
# Should show: cgroup_enable=memory swapaccount=1 systemd.unified_cgroup_hierarchy=0
```

### Quick Install

Install via pip:

```bash
pip install domjudge-cli
```

Verify installation:
```bash
dom --version
```

---

## Quick Start

Get up and running in 3 commands:

```bash
# 1. Initialize configuration
dom init

# 2. Deploy infrastructure
dom infra apply

# 3. Apply contest configuration
dom contest apply
```

This will:
1. Create a `dom-judge.yaml` configuration file with an interactive wizard
2. Deploy DOMjudge server, database, and judgehosts in Docker containers
3. Configure contests, problems, and teams on the platform

---

## Command Reference

### Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable detailed logging output |
| `--no-color` | Disable colored terminal output |
| `--version`, `-v` | Show CLI version and exit |
| `--help` | Show help message and exit |

**Example:**
```bash
dom --verbose infra status
```

---

### dom init

Initialize a new DOMjudge configuration file.

```bash
dom init [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--overwrite` | flag | `false` | Overwrite existing `dom-judge.yaml` if present |
| `--dry-run` | flag | `false` | Preview files that would be created without creating them |

#### Behavior

- Launches an interactive wizard to configure infrastructure and contests
- Creates `dom-judge.yaml` in the current directory
- Fails if `dom-judge.yaml` already exists (unless `--overwrite` is used)
- Automatically discovers and uses `dom-judge.yaml` or `dom-judge.yml` for subsequent commands

#### Examples

**Basic initialization:**
```bash
dom init
```

**Preview what would be created:**
```bash
dom init --dry-run
```

**Overwrite existing configuration:**
```bash
dom init --overwrite
```

---

### dom infra

Manage DOMjudge infrastructure and platform resources.

#### Commands

- [`dom infra apply`](#dom-infra-apply) - Deploy or update infrastructure
- [`dom infra destroy`](#dom-infra-destroy) - Tear down infrastructure
- [`dom infra status`](#dom-infra-status) - Check infrastructure health

---

#### dom infra apply

Deploy or update infrastructure based on configuration file.

```bash
dom infra apply [OPTIONS]
```

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | path | `dom-judge.yaml` | Path to configuration YAML file |
| `--dry-run` | flag | `false` | Preview changes without applying |
| `--verbose` | flag | `false` | Enable detailed output |

##### What It Does

1. **Reads** the infrastructure configuration from YAML
2. **Deploys** Docker containers:
   - DOMserver (web interface and API)
   - MariaDB (database)
   - Judgehosts (code execution workers)
   - MySQL client (database management)
3. **Configures** authentication and networking
4. **Validates** deployment was successful

##### Examples

**Deploy with default config:**
```bash
dom infra apply
```

**Deploy with custom config:**
```bash
dom infra apply --file my-contest.yaml
```

**Preview deployment without applying:**
```bash
dom infra apply --dry-run
```

**Deploy with verbose logging:**
```bash
dom infra apply --verbose
```

##### Exit Codes

- `0` - Success
- `1` - Failure (check logs for details)

---

#### dom infra destroy

Destroy all infrastructure and platform resources.

```bash
dom infra destroy [OPTIONS]
```

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--confirm` | flag | `false` | **Required**. Confirm destruction |
| `--force-delete-volumes` | flag | `false` | Permanently delete Docker volumes (DATA LOSS) |
| `--dry-run` | flag | `false` | Preview what would be destroyed |

##### What It Does

1. **Stops** all DOMjudge containers
2. **Removes** containers from Docker
3. **Preserves** volumes (unless `--force-delete-volumes` is used)
4. **Cleans up** networks and resources

##### Data Preservation

**By default, Docker volumes are PRESERVED** to prevent accidental data loss. This includes:
- Contest data
- Database contents
- Submission history
- Team information

To completely remove all data, use `--force-delete-volumes`.

##### Examples

**Destroy infrastructure (preserves data):**
```bash
dom infra destroy --confirm
```

**Completely remove everything (DATA LOSS):**
```bash
dom infra destroy --confirm --force-delete-volumes
```

**Preview what would be destroyed:**
```bash
dom infra destroy --dry-run
```

##### Exit Codes

- `0` - Success
- `1` - Failure or missing `--confirm`

##### Safety Features

- Requires explicit `--confirm` flag to prevent accidental destruction
- Shows warning before deleting volumes
- Dry-run mode for safe preview

---

#### dom infra status

Check the health status of DOMjudge infrastructure.

```bash
dom infra status [OPTIONS]
```

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | path | optional | Configuration file (for expected judgehost count) |
| `--json` | flag | `false` | Output in JSON format |
| `--verbose` | flag | `false` | Enable detailed output |

##### What It Checks

- ✓ Docker daemon availability
- ✓ DOMserver container status
- ✓ MariaDB container status
- ✓ Judgehost containers (expected vs actual count)
- ✓ MySQL client container status
- ✓ Network connectivity

##### Examples

**Check status:**
```bash
dom infra status
```

**Check status with expected configuration:**
```bash
dom infra status --file dom-judge.yaml
```

**Output status as JSON:**
```bash
dom infra status --json
```

##### Exit Codes

- `0` - All systems healthy
- `1` - One or more systems unhealthy

##### Use Cases

- Health checks in CI/CD pipelines
- Monitoring scripts
- Pre-contest validation
- Debugging infrastructure issues

---

### dom contest

Manage contests, problems, and teams on the DOMjudge platform.

#### Commands

- [`dom contest apply`](#dom-contest-apply) - Apply contest configuration
- [`dom contest verify-problemset`](#dom-contest-verify-problemset) - Verify problem correctness
- [`dom contest inspect`](#dom-contest-inspect) - Inspect loaded configuration

---

#### dom contest apply

Apply contest configuration to the platform.

```bash
dom contest apply [OPTIONS]
```

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | path | `dom-judge.yaml` | Path to configuration YAML file |
| `--dry-run` | flag | `false` | Preview changes without applying |
| `--verbose` | flag | `false` | Enable detailed output |

##### What It Does

1. **Loads** configuration from YAML
2. **Creates/updates** contests on the platform
3. **Uploads** problem packages (with validation)
4. **Registers** teams and affiliations
5. **Configures** contest settings (duration, penalties, etc.)

##### Safe Live Updates

This command is designed for **live operations** and can safely update contests while the platform is running:
- Non-destructive updates to existing contests
- Preserves existing data
- Atomic operations with rollback on failure

##### Examples

**Apply contest configuration:**
```bash
dom contest apply
```

**Apply with custom config:**
```bash
dom contest apply --file my-contest.yaml
```

**Preview changes without applying:**
```bash
dom contest apply --dry-run
```

**Apply with detailed logging:**
```bash
dom contest apply --verbose
```

##### Exit Codes

- `0` - Success
- `1` - Failure (check logs for details)

---

#### dom contest verify-problemset

Verify the problemset of a contest by running sample submissions.

```bash
dom contest verify-problemset CONTEST_NAME [OPTIONS]
```

##### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CONTEST_NAME` | string | Yes | Name or shortname of the contest |

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | path | `dom-judge.yaml` | Path to configuration YAML file |
| `--dry-run` | flag | `false` | Preview what would be verified |
| `--verbose` | flag | `false` | Enable detailed output |

##### What It Does

1. **Identifies** all problems in the contest
2. **Runs** sample submissions for each problem
3. **Validates** results against expected outcomes
4. **Checks** performance limits (time, memory)
5. **Reports** per-problem summaries including:
   - Correct/incorrect submissions
   - Performance metrics
   - Mismatches and warnings

##### Examples

**Verify problemset for a contest:**
```bash
dom contest verify-problemset "ICPC Regional 2025"
```

**Verify with custom config:**
```bash
dom contest verify-problemset SAMPLE2025 --file config.yaml
```

**Preview verification without running:**
```bash
dom contest verify-problemset SAMPLE2025 --dry-run
```

##### Exit Codes

- `0` - All problems verified successfully
- `1` - Verification failed or problems detected

##### Use Cases

- Pre-contest validation
- Problem package testing
- Automated quality assurance
- Contest dry runs

---

#### dom contest inspect

Inspect loaded configuration with optional filtering.

```bash
dom contest inspect [OPTIONS]
```

##### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | path | `dom-judge.yaml` | Path to configuration YAML file |
| `--format` | string | none | JMESPath expression to filter output |
| `--show-secrets` | flag | `false` | Include secret values (otherwise masked) |
| `--verbose` | flag | `false` | Enable detailed output |

##### What It Does

1. **Loads** configuration from YAML
2. **Parses** all contests, problems, and teams
3. **Outputs** structured JSON
4. **Masks** sensitive data (unless `--show-secrets`)
5. **Filters** output (if `--format` provided)

##### Examples

**Inspect full configuration:**
```bash
dom contest inspect
```

**Show configuration with secrets:**
```bash
dom contest inspect --show-secrets
```

**Filter to show only contest names:**
```bash
dom contest inspect --format "[].name"
```

**Show problems for first contest:**
```bash
dom contest inspect --format "[0].problems[].short_name"
```

**Count total teams across all contests:**
```bash
dom contest inspect --format "length([].teams[])"
```

##### JMESPath Examples

JMESPath is a query language for JSON. Common patterns:

```bash
# Get all contest names
--format "[].name"

# Get first contest details
--format "[0]"

# Get all problems from all contests
--format "[].problems[]"

# Filter contests by name
--format "[?name=='ICPC Regional 2025']"

# Get team count per contest
--format "[].[name, length(teams)]"
```

##### Exit Codes

- `0` - Success
- `1` - Failure (invalid config or filter)

---

## Configuration

DOMjudge CLI uses YAML configuration files to define infrastructure and contests.

### Configuration File Structure

The configuration file has two main sections:

```yaml
infra:
  # Infrastructure configuration
  port: 8080
  judges: 2
  password: "secure_password"

contests:
  # List of contests
  - name: "Contest Name"
    shortname: "CONTEST2025"
    # ... contest configuration
```

### Configuration File Discovery

By default, the CLI looks for configuration files in this order:
1. `dom-judge.yaml`
2. `dom-judge.yml`

You can override this with `--file` option:
```bash
dom infra apply --file custom-config.yaml
```

---

### Infrastructure Configuration

Define infrastructure settings under the `infra:` key.

#### Schema

```yaml
infra:
  port: <integer>          # DOMserver port (required)
  judges: <integer>        # Number of judgehost workers (required)
  password: <string>       # Admin password (required)
```

#### Example

```yaml
infra:
  port: 8080
  judges: 4
  password: "YourSecurePassword123"
```

#### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `port` | integer | Yes | Port for DOMserver web interface (1024-65535) |
| `judges` | integer | Yes | Number of judgehost containers (1-32 recommended) |
| `password` | string | Yes | Admin password for DOMjudge (min 8 characters) |

#### Best Practices

- **Port**: Use ports 8080-8090 to avoid conflicts
- **Judges**: Allocate 1 judge per 2 CPU cores available
- **Password**: Use strong passwords (16+ characters, mixed case, numbers, symbols)

---

### Contest Configuration

Define contests under the `contests:` key as a list.

#### Schema

```yaml
contests:
  - name: <string>                  # Contest display name (required)
    shortname: <string>             # Contest identifier (required)
    start_time: <datetime>          # ISO 8601 format (required)
    duration: <duration>            # HH:MM:SS.mmm format (required)
    penalty_time: <integer>         # Minutes penalty per wrong submission
    allow_submit: <boolean>         # Allow submissions (default: true)
    
    problems:                        # Problem configuration (see below)
      # ... problems
    
    teams:                           # Team configuration (see below)
      # ... teams
```

#### Example

```yaml
contests:
  - name: "ICPC Regional Championship 2025"
    shortname: "ICPC2025"
    start_time: "2025-06-15T09:00:00+00:00"
    duration: "05:00:00.000"
    penalty_time: 20
    allow_submit: true
    
    problems:
      from: "problems.yaml"
    
    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-100"
      name: "$2"
      affiliation: "$3"
```

#### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable contest name |
| `shortname` | string | Yes | Unique identifier (alphanumeric, no spaces) |
| `start_time` | datetime | Yes | Contest start time (ISO 8601 format with timezone) |
| `duration` | duration | Yes | Contest duration (HH:MM:SS.mmm) |
| `penalty_time` | integer | Yes | Penalty minutes for wrong submissions |
| `allow_submit` | boolean | No | Enable/disable submissions (default: true) |
| `problems` | object | Yes | Problem configuration (see below) |
| `teams` | object | Yes | Team configuration (see below) |

#### Date/Time Format

Use ISO 8601 format with timezone:
```yaml
start_time: "2025-06-15T09:00:00+00:00"  # UTC
start_time: "2025-06-15T14:00:00+05:00"  # UTC+5
start_time: "2025-06-15T04:00:00-05:00"  # UTC-5
```

#### Duration Format

Format: `HH:MM:SS.mmm`
```yaml
duration: "05:00:00.000"  # 5 hours
duration: "03:30:00.000"  # 3.5 hours
duration: "02:00:00.000"  # 2 hours
```

---

### Problem Configuration

Define problems for a contest. Two approaches are supported:

#### Approach 1: Inline Problems

Define problems directly in the contest configuration:

```yaml
contests:
  - name: "My Contest"
    shortname: "CONTEST2025"
    # ... other fields
    
    problems:
      - archive: problems/two-sum.zip
        platform: "Polygon"
        color: blue
      
      - archive: problems/graph-traversal.zip
        platform: "Polygon"
        color: green
      
      - archive: problems/dynamic-programming.zip
        platform: "Polygon"
        color: red
```

#### Approach 2: External Problem File

Reference an external YAML file:

```yaml
contests:
  - name: "My Contest"
    shortname: "CONTEST2025"
    # ... other fields
    
    problems:
      from: "problems.yaml"
```

**problems.yaml:**
```yaml
- archive: problems/two-sum.zip
  platform: "Polygon"
  color: blue

- archive: problems/graph-traversal.zip
  platform: "Polygon"
  color: green

- archive: problems/dynamic-programming.zip
  platform: "Polygon"
  color: red
```

#### Problem Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `archive` | path | Yes | Path to problem package (ZIP format) |
| `platform` | string | Yes | Problem source platform (`"Polygon"`, `"Kattis"`, `"DOMjudge"`) |
| `color` | string | No | Problem color in scoreboard (see below) |

#### Supported Colors

Valid color values:
- `blue`, `green`, `red`, `yellow`, `orange`, `purple`, `pink`, `cyan`, `brown`, `gray`, `black`, `white`

Or use hex codes:
```yaml
color: "#FF5733"
```

#### Problem Package Requirements

**Polygon Format:**
- Export package with **Linux** type (not Windows or Standard)
- ZIP file must contain `problem.xml` and test data

**File Structure:**
```
problem-name.zip
├── problem.xml
├── statements/
├── tests/
└── solutions/
```

#### Multiple Contests Sharing Problems

You can reuse the same problem file across multiple contests:

```yaml
contests:
  - name: "Practice Contest"
    shortname: "PRACTICE"
    problems:
      from: "problems.yaml"
  
  - name: "Official Contest"
    shortname: "OFFICIAL"
    problems:
      from: "problems.yaml"  # Same problems
```

---

### Team Configuration

Define teams for a contest. Two approaches are supported:

#### Approach 1: CSV/TSV File

Reference an external CSV or TSV file:

```yaml
contests:
  - name: "My Contest"
    shortname: "CONTEST2025"
    # ... other fields
    
    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-100"
      name: "$2"
      affiliation: "$3"
      country: "USA"  # Optional: fixed country for all teams
```

**teams.csv:**
```csv
id,name,affiliation,email
1,Team Alpha,MIT,alpha@mit.edu
2,Team Beta,Stanford,beta@stanford.edu
3,Team Gamma,Berkeley,gamma@berkeley.edu
```

#### Team Configuration Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | path | Yes | Path to CSV/TSV file |
| `delimiter` | string | Yes | Field delimiter (`,` for CSV, `\t` for TSV) |
| `rows` | string | Yes | Row range to import (e.g., `"2-100"`, `"2-"`, `"1-50"`) |
| `name` | string | Yes | Column reference for team name (e.g., `"$2"`) |
| `affiliation` | string | Yes | Column reference for affiliation (e.g., `"$3"`) |
| `country` | string | No | Fixed country code for all teams |
| `email` | string | No | Column reference for email (e.g., `"$4"`) |

#### Column References

Use `$N` notation to reference columns (1-indexed):
- `$1` = First column
- `$2` = Second column
- `$3` = Third column
- etc.

#### Row Range Format

Specify which rows to import:
- `"2-100"` = Rows 2 through 100 (skips header)
- `"2-"` = Rows 2 to end of file
- `"1-50"` = First 50 rows

#### Examples

**CSV with header:**
```yaml
teams:
  from: "teams.csv"
  delimiter: ","
  rows: "2-"        # Skip header row
  name: "$2"        # Second column
  affiliation: "$3" # Third column
```

**TSV without header:**
```yaml
teams:
  from: "teams.tsv"
  delimiter: "\t"
  rows: "1-"        # Include all rows
  name: "$1"        # First column
  affiliation: "$2" # Second column
```

**With country code:**
```yaml
teams:
  from: "teams.csv"
  delimiter: ","
  rows: "2-"
  name: "$2"
  affiliation: "$3"
  country: "USA"    # All teams from USA
```

#### Approach 2: Inline Teams (Advanced)

Define teams directly in YAML (for small contests):

```yaml
contests:
  - name: "My Contest"
    teams:
      - name: "Team Alpha"
        affiliation: "MIT"
        country: "USA"
      
      - name: "Team Beta"
        affiliation: "Stanford"
        country: "USA"
```

---

## Usage Examples

### Complete Workflow

From initialization to contest deployment:

```bash
# 1. Initialize configuration
dom init

# 2. Edit configuration file
vim dom-judge.yaml

# 3. Preview infrastructure deployment
dom infra apply --dry-run

# 4. Deploy infrastructure
dom infra apply

# 5. Verify infrastructure is healthy
dom infra status

# 6. Preview contest configuration
dom contest apply --dry-run

# 7. Apply contest configuration
dom contest apply

# 8. Verify problemset
dom contest verify-problemset "ICPC2025"

# 9. Inspect configuration
dom contest inspect --format "[].name"
```

---

### Example: Multi-Contest Setup

**dom-judge.yaml:**
```yaml
infra:
  port: 8080
  judges: 8
  password: "SecurePassword123"

contests:
  # Practice contest
  - name: "ICPC 2025 Practice"
    shortname: "ICPC2025-PRACTICE"
    start_time: "2025-06-14T14:00:00+00:00"
    duration: "02:00:00.000"
    penalty_time: 20
    allow_submit: true
    
    problems:
      from: "practice-problems.yaml"
    
    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-"
      name: "$2"
      affiliation: "$3"
  
  # Official contest
  - name: "ICPC 2025 Official"
    shortname: "ICPC2025-OFFICIAL"
    start_time: "2025-06-15T09:00:00+00:00"
    duration: "05:00:00.000"
    penalty_time: 20
    allow_submit: true
    
    problems:
      from: "official-problems.yaml"
    
    teams:
      from: "teams.csv"
      delimiter: ","
      rows: "2-"
      name: "$2"
      affiliation: "$3"
```

**Deploy:**
```bash
# Deploy infrastructure
dom infra apply

# Apply both contests
dom contest apply

# Verify both problemsets
dom contest verify-problemset "ICPC2025-PRACTICE"
dom contest verify-problemset "ICPC2025-OFFICIAL"
```

---

### Example: Update Existing Contest

Update contest configuration without downtime:

```bash
# 1. Edit configuration file
vim dom-judge.yaml

# 2. Preview changes
dom contest apply --dry-run

# 3. Apply changes (safe for live contests)
dom contest apply
```

---

### Example: Scale Judgehosts

Increase judgehost capacity:

```bash
# 1. Edit configuration
vim dom-judge.yaml
# Change: judges: 8

# 2. Preview changes
dom infra apply --dry-run

# 3. Apply changes
dom infra apply

# 4. Verify new judgehosts are running
dom infra status
```

---

### Example: CI/CD Integration

Automated deployment pipeline:

```bash
#!/bin/bash
set -e

# Validate configuration
dom init --dry-run

# Deploy infrastructure
dom infra apply --verbose

# Wait for infrastructure to be ready
until dom infra status --json | jq -e '.healthy == true'; do
  echo "Waiting for infrastructure..."
  sleep 5
done

# Apply contest configuration
dom contest apply --verbose

# Verify problemsets
for contest in $(dom contest inspect --format '[].shortname' | jq -r '.[]'); do
  dom contest verify-problemset "$contest"
done

echo "Deployment successful!"
```

---

### Example: Monitoring Script

Health check script for production:

```bash
#!/bin/bash

# Check infrastructure health
if ! dom infra status --json > /tmp/status.json; then
  echo "ERROR: Infrastructure unhealthy"
  cat /tmp/status.json
  exit 1
fi

# Parse JSON output
healthy=$(jq -r '.healthy' /tmp/status.json)
judges_running=$(jq -r '.judges.running' /tmp/status.json)
judges_expected=$(jq -r '.judges.expected' /tmp/status.json)

if [ "$healthy" = "true" ]; then
  echo "✓ Infrastructure healthy"
  echo "✓ Judges: $judges_running/$judges_expected running"
  exit 0
else
  echo "✗ Infrastructure unhealthy"
  exit 1
fi
```

---

## Advanced Topics

### Environment Variables

Control CLI behavior with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DOM_CONFIG_FILE` | Default configuration file | `dom-judge.yaml` |
| `DOM_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `DOM_NO_COLOR` | Disable colored output | `false` |
| `DOCKER_HOST` | Docker daemon address | `unix:///var/run/docker.sock` |

**Example:**
```bash
export DOM_LOG_LEVEL=DEBUG
export DOM_NO_COLOR=true
dom infra apply
```

---

### Secrets Management

The CLI stores sensitive data securely in `~/.dom/secrets.enc`.

**View secrets:**
```bash
cat ~/.dom/secrets.enc
```

**Secrets stored:**
- Admin passwords
- Database credentials
- API keys
- Judgedaemon authentication tokens

**Security best practices:**
- Never commit `~/.dom/secrets.enc` to version control
- Rotate passwords regularly
- Use strong passwords (16+ characters)

---

### Docker Configuration

The CLI creates Docker resources with specific naming conventions:

**Containers:**
- `domserver` - Web interface and API
- `mariadb` - Database server
- `judgehost-{n}` - Judgehost workers (n = 0, 1, 2, ...)
- `mysql-client` - Database management

**Networks:**
- `domjudge-network` - Internal network for containers

**Volumes:**
- `domserver-data` - DOMserver persistent data
- `mariadb-data` - Database data

**Inspect Docker resources:**
```bash
docker ps                      # List containers
docker network ls              # List networks
docker volume ls               # List volumes
```

---

### Debugging

Enable verbose logging for troubleshooting:

```bash
# Verbose output
dom --verbose infra status

# Check logs
tail -f ~/.dom/domjudge-cli.log

# Docker logs
docker logs domserver
docker logs mariadb
docker logs judgehost-0
```

---

### Performance Tuning

**Judgehost Allocation:**
- **Light load** (< 100 teams): 2-4 judgehosts
- **Medium load** (100-300 teams): 4-8 judgehosts
- **Heavy load** (300+ teams): 8-16 judgehosts

**Resource Requirements:**
- **CPU**: 2 cores per judgehost
- **RAM**: 2GB per judgehost
- **Disk**: 10GB minimum for system, 50GB+ for contests

**Example for 500 teams:**
```yaml
infra:
  port: 8080
  judges: 12      # 12 judgehosts for high throughput
  password: "..."
```

---

## Troubleshooting

### Common Issues

#### Issue: "Docker daemon not available"

**Symptoms:**
```
ERROR: Cannot connect to Docker daemon
```

**Solution:**
```bash
# Start Docker
sudo systemctl start docker

# Verify Docker is running
docker ps
```

---

#### Issue: "Port already in use"

**Symptoms:**
```
ERROR: Port 8080 is already allocated
```

**Solution:**
```bash
# Find process using port
sudo lsof -i :8080

# Kill process or change port in configuration
vim dom-judge.yaml
# Change: port: 8081
```

---

#### Issue: "Judgehosts not starting"

**Symptoms:**
```
WARNING: Expected 4 judgehosts, found 0 running
```

**Solution:**
```bash
# Verify cgroups are enabled
cat /proc/cmdline | grep cgroup_enable

# If not enabled, follow installation steps
sudo vi /etc/default/grub.d/99-domjudge-cgroups.cfg
sudo update-grub
sudo reboot
```

---

#### Issue: "Configuration file not found"

**Symptoms:**
```
ERROR: Configuration file not found: dom-judge.yaml
```

**Solution:**
```bash
# Initialize configuration
dom init

# Or specify file explicitly
dom infra apply --file /path/to/config.yaml
```

---

#### Issue: "Problem upload failed"

**Symptoms:**
```
ERROR: Failed to upload problem package
```

**Solution:**
```bash
# Verify problem package format
unzip -l problems/problem-name.zip

# Ensure Polygon export type is "Linux"
# Re-export from Polygon with Linux format

# Verify file path is correct
ls -la problems/
```

---

#### Issue: "Authentication failed"

**Symptoms:**
```
ERROR: Failed to authenticate with DOMjudge API
```

**Solution:**
```bash
# Check admin password in configuration
vim dom-judge.yaml

# Reset secrets
rm -rf ~/.dom/secrets.enc
dom infra destroy --confirm
dom infra apply
```

---

### Getting Help

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -f ~/.dom/domjudge-cli.log
   ```

2. **Enable verbose mode:**
   ```bash
   dom --verbose infra status
   ```

3. **Check Docker logs:**
   ```bash
   docker logs domserver
   ```

4. **Verify system requirements:**
   ```bash
   cat /proc/cmdline | grep cgroup_enable
   docker --version
   python --version
   ```

5. **Report issues:**
   - GitHub: https://github.com/AnasImloul/domjudge-cli/issues
   - Include: CLI version, OS, logs, and configuration (redact secrets)

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Links

- **Homepage:** https://github.com/AnasImloul/domjudge-cli
- **PyPI:** https://pypi.org/project/domjudge-cli/
- **Issues:** https://github.com/AnasImloul/domjudge-cli/issues
- **DOMjudge:** https://www.domjudge.org/

---

**Built with ❤️ for the competitive programming community.**
