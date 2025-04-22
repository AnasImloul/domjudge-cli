# dom-cli

`dom-cli` is a command-line tool for setting up and managing coding contests in DOMjudge. `dom-cli` enables you to define one or more contests along with their problems, teams, and outputs using simple configuration files. With its incremental update mechanism, you can modify contest settings without restarting the DOMjudge server, thereby preserving volatile data and avoiding lengthy re-deployments.

## Key Features

- Declarative Multiple Contest Definitions: Define multiple contests within a single YAML config file.
- Grouped Contest Resources: Each contest entry includes its own problems, teams, and contest-specific configuration for clearer and more intuitive management.
- Incremental Updates: Apply only the changes that have been made without restarting the DOMjudge server.
- Terraform-Inspired Resource Management: Use a familiar, structured approach to control and deploy contest infrastructure.
- Flexible Input Formats: Supports YAML for configurations and TSV for team definitions.

## Installation

```bash
pip install dom-cli
```

## Usage

Apply your configuration file using the CLI. By default, `dom-cli` will look for a file named `dom-config.yaml` or `dom-config.yml`.

```bash
dom apply -f dom-config.yaml
```

## Configuration Files

The configuration file supports multiple contests by using the `contests` section. Each contest entry contains its own configuration, as well as its associated problems and teams definitions. You can also define global outputs to extract useful data, such as team passwords.

### Example: dom-config.yaml

```yaml
version: "1.0"

# Define multiple contests in one configuration file
contests:
  - name: "JNJD2024"
    formal_name: "JNJD2024"
    id: "2"
    penalty_time: 20
    start_time: "2024-05-12T11:00:00+07:00"
    end_time: "2024-05-12T15:00:00+07:00"
    duration: "4:00:00.000"
    scoreboard_freeze_duration: "1:00:00.000"
    external_id: "JNJD2024"
    name: "JNJD Programming Contest 2024"
    shortname: "JNJD2024"
    allow_submit: true
    problems:
      from: 'problems-jnjd.yml'
    teams:
      from: 'teams-jnjd.tsv'
      rows: "2-75"
      name: "$1"

# Global outputs can extract details from one or more contests
outputs:
  team_passwords:
    description: "Display team passwords for all contests"
    value: "contests.*.teams.passwords"
    format: "json"
    file: "passwords.json"
```

### Explanation of the Config Structure

- `version`: The version of your configuration schema.
- `contests`: A list where each item is a contest definition.
  - `name`: A unique identifier for the contest entry within the configuration (can be used as a reference).
  - `contest`: Contains contest-specific settings (start time, penalty settings, duration, etc.).
  - `problems`: Points to the file (or inline definitions) containing the contest’s problems.
  - `teams`: Refers to the file (typically TSV) that lists the teams, along with any row filtering and naming template.
- `outputs`: Define outputs to extract or compute additional information after applying your configuration (e.g., team passwords).

## Incremental Updates Without Server Restart

One of the main advantages of using `dom-cli` is its ability to apply updates incrementally:

- **Selective Resource Updates:** Only the resources (contests, problems, teams) that have been modified will be updated.
- **Live System Continuity:** By not restarting the DOMjudge server, volatile contest data remains intact.
- **Faster Deployments:** The deployment process becomes faster and more efficient, especially during live contests.
