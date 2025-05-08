# domjudge-cli

`domjudge-cli` is a command-line tool to set up and manage coding contests on **DOMjudge**.  
It enables you to **declaratively define infrastructure, contests, problems, and teams** using simple configuration files.

Built for **live operations**, it safely applies updates to the platform without requiring downtime.

---

## Key Features

- **Declarative Infrastructure and Contest Management:** Manage everything with YAML files.
- **Infrastructure as Code:** Deploy DOMjudge servers and judgehosts with a single command.
- **Incremental Changes:** Update infrastructure or contests without downtime.
- **Flexible Input Formats:** YAML for configuration; CSV/TSV for teams.
- **Safe Live Modifications:** Apply contest changes while DOMjudge is running.
- **Automatic Config Discovery:** If `--file` is not specified, it will automatically use `dom-judge.yaml` or `dom-judge.yml` (whichever exists first in the current directory).

---

## Installation

```
pip install domjudge-cli
```

Before using `domjudge-cli` to deploy infrastructure, ensure that **cgroups** are enabled on your OS (currently supporting **Ubuntu 22.04**).

1. Create or edit the GRUB configuration:
   
   ```
   sudo vi /etc/default/grub.d/99-domjudge-cgroups.cfg
   ```

   Insert the following line:
   
   ```
   GRUB_CMDLINE_LINUX_DEFAULT="cgroup_enable=memory swapaccount=1 systemd.unified_cgroup_hierarchy=0"
   ```

2. Update GRUB and reboot:

   ```
   sudo update-grub
   sudo reboot
   ```

Only after completing these steps should you attempt to run `domjudge-cli` infrastructure commands.

---

## CLI Usage

Run `dom --help` to see available commands:

```
dom --help
```

Main command groups:

| Command Group | Purpose |
|:--------------|:--------|
| `dom infra` | Manage infrastructure and platform setup |
| `dom contest` | Manage contests and related configuration |

---

### 1. Manage Infrastructure

Apply or destroy infrastructure resources.

- **Apply Infrastructure:**

```
dom infra apply --file dom-judge.yaml
```

- **Destroy Infrastructure:**

```
dom infra destroy --confirm
```

If no `--file` is provided, defaults to `dom-judge.yaml` or `dom-judge.yml`.

---

### 2. Manage Contests

Apply contest settings to a running platform.

- **Apply Contest Configuration:**

```
dom contest apply --file dom-judge.yaml
```

If no `--file` is provided, defaults to `dom-judge.yaml` or `dom-judge.yml`.

---

## Configuration Files

Everything is controlled via configuration files in YAML format.

Example: `dom-judge.yaml`

```
infra:
  port: 8080
  judges: 2
  password: "your_admin_password_here"

contests:
  - name: "Sample Contest"
    shortname: "SAMPLE2025"
    start_time: "2025-06-01T10:00:00+00:00"
    duration: "5:00:00.000"
    penalty_time: 20
    allow_submit: true

    problems:
      from: "problems.yaml"

    teams:
      from: "teams.csv"
      delimiter: ','
      rows: "2-50"
      name: "$2"
```

Supporting file example: `problems.yaml`

```
- archive: problems/example-problem-1.zip
  platform: "Polygon"
  color: blue

- archive: problems/example-problem-2.zip
  platform: "Polygon"
  color: green

- archive: problems/example-problem-3.zip
  platform: "Polygon"
  color: yellow
```

---

### Problem Declarations

- Problems for a contest can be **defined directly inside** the contest `problems:` section like this:

```
problems:
  - archive: problems/sample-problem.zip
    platform: "Polygon"
    color: blue
```

- Or you can **abstract the problem list** into a **separate YAML file** and reference it like this:

```
problems:
  from: "problems.yaml"
```

Choose whichever structure better suits your project organization.

---

## Typical Workflow

```
# Apply infrastructure
dom infra apply --file dom-judge.yaml

# Apply contests, problems, and teams
dom contest apply --file dom-judge.yaml

# (Optional) Destroy infrastructure when done
dom infra destroy --confirm
```

---

## Contest Commands

- `dom contest verify-problemset CONTEST_NAME`: Verify the problemset of the specified contest by running sample submissions to ensure correctness, completeness, and performance limits are met, then report per-problem summaries including mismatches and warnings.

---

## Notes

- Requires Docker installed for infrastructure operations.
- Ensure **cgroups** are properly configured and the system has been rebooted as per Installation instructions.
- DOMjudge API credentials are automatically handled or can be configured.
- Problems and teams must be correctly referenced in the config YAML.
- If no configuration file is explicitly passed with `--file`, the CLI will look for `dom-judge.yaml` or `dom-judge.yml`.

---

# 🎯 Summary

| Action              | Command                                     |
|:--------------------|:--------------------------------------------|
| Deploy platform     | ```dom infra apply --file dom-judge.yaml``` |
| Configure contests  | ```dom contest apply --file dom-judge.yaml```|
| Verify problemset   | ```dom contest verify-problemset CONTEST_NAME``` |
| Destroy everything  | ```dom infra destroy --confirm```           |

---