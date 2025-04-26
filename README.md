# dom-cli

`dom-cli` is a command-line tool for setting up and managing coding contests in **DOMjudge**.  
It enables you to **declaratively define infrastructure, contests, problems, and teams** using simple configuration files.

With its incremental update mechanism, you can modify contest settings without restarting the DOMjudge server — preserving live data and avoiding lengthy redeployments.

---

## Key Features

- **Declarative Infrastructure and Contest Management:** Use YAML files to describe the full environment.
- **Infrastructure as Code:** Manage DOMjudge servers and judgehosts with a single command.
- **Problemset Validation:** Validate your problem solutions against expected outcomes easily.
- **Incremental Updates:** Apply only the changes needed, no server restarts.
- **Flexible Input Formats:** Supports YAML for configs and TSV/CSV for team definitions.
- **Safe Live Operations:** Built for zero-downtime contest management.

---

## Installation

```bash
pip install dom-cli
```

---

## Usage

`dom-cli` is split into **three main command groups**:

| Command Group | Purpose |
|:--------------|:--------|
| `dom infra` | Manage Docker infrastructure for DOMjudge (start/stop/update containers) |
| `dom contest` | Manage contests, teams, submissions, scoreboard |
| `dom problemset` | Manage and validate problem archives, solutions |

---

### 1. Infrastructure Management

```bash
dom infra up -f dom-config.yaml    # Start mariadb + domserver + judgehosts
dom infra down                     # Stop and remove containers
dom infra status                   # Check running containers
```

---

### 2. Contest Management

```bash
dom contest plan -f dom-config.yaml   # Preview contest changes
dom contest apply -f dom-config.yaml  # Apply contests, teams, problems
dom contest destroy --confirm         # Destroy contests and teams
```

---

### 3. Problemset Management

```bash
dom problemset validate -f problems-jnjd.yml
```

- Validates all provided solutions (AC, WA, TLE, etc.) against the problem definitions.
- Ensures problem tags match actual results.

---

## Configuration Files

You manage everything via a single config file, usually called `dom-config.yaml`.

Example:

```yaml
infra:
  port: 12345
  judges: 4

contests:
  - name: "JNJD2024"
    formal_name: "JNJD Programming Contest 2024"
    start_time: "2024-05-12T11:00:00+07:00"
    end_time: "2024-05-12T15:00:00+07:00"
    penalty_time: 20
    allow_submit: true
    
    problems:
      from: "problems-jnjd.yaml"
    
    teams:
      from: "teams-jnjd.csv"
      rows: "2-75"
      name: "$1"
```

---

### Explanation of the Config Structure

- `infra`: Configuration for the infrastructure (ports, judgehost count, etc.).
- `contests`: List of contests to create, each with their own problems and teams.
- `problems`: Path to external YAML files defining problemsets.
- `teams`: Path to team information in TSV format.

---

## Incremental Updates Without Server Restart

- **Selective Updates:** Only modified resources are updated.
- **Live Data Preservation:** No DOMjudge restart needed.
- **Faster Contest Preparation:** Especially useful during active contests or last-minute changes.

---

# 📜 Example Full Workflow

```bash
# Set up infrastructure
dom infra up -f dom-config.yaml

# Plan contest changes
dom contest plan -f dom-config.yaml

# Apply contests, problems, teams
dom contest apply -f dom-config.yaml

# Validate problemset before live
dom problemset validate -f problems-jnjd.yaml
```

---

# 📢 Notes

- Make sure Docker is installed for `infra` commands.
- DOMjudge API credentials will be picked up automatically or configured manually.
- Problemset validation requires providing correct test solutions.

---
