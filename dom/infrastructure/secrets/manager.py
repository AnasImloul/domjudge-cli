import os
import json
import secrets
import string
from dom.utils.cli import ensure_dom_directory
import random

SECRETS_FILE = os.path.join(ensure_dom_directory(), "secrets.json")

def generate_random_string(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def load_or_generate_secret(key: str, length: int = 16) -> str:
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    # Return if already exists
    if key in secrets_data:
        return secrets_data[key]

    # Otherwise, generate and save
    secrets_data[key] = generate_random_string(length)
    with open(SECRETS_FILE, "w") as f:
        json.dump(secrets_data, f, indent=2)

    return secrets_data[key]

def load_or_save_secret(key: str, value):
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    # Return if already exists
    if key in secrets_data:
        return secrets_data[key]

    # Otherwise, generate and save
    secrets_data[key] = value
    with open(SECRETS_FILE, "w") as f:
        json.dump(secrets_data, f, indent=2)

    return secrets_data[key]


def load_secret(key: str):
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    return secrets_data[key]


def save_secret_if_not_exists(key: str, value):
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    # Return if already exists
    if key in secrets_data:
        return

    # Otherwise, generate and save
    secrets_data[key] = value
    with open(SECRETS_FILE, "w") as f:
        json.dump(secrets_data, f, indent=2)


def save_secret(key: str, value):
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    # generate and save
    secrets_data[key] = value
    with open(SECRETS_FILE, "w") as f:
        json.dump(secrets_data, f, indent=2)

    return secrets_data[key]


def load_or_default_secret(key: str, default_value=None):
    # Make sure generated folder exists
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)

    # Load secrets if file exists
    if os.path.isfile(SECRETS_FILE):
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
    else:
        secrets_data = {}

    # Return if already exists
    if key in secrets_data:
        return secrets_data[key]
    else:
        return default_value

def clear_secrets() -> None:
    if os.path.exists(SECRETS_FILE):
        os.remove(SECRETS_FILE)

def generate_secure_password(length: int, seed: str) -> str:
    # Load the admin_password from secrets
    admin_password = load_secret("admin_password")

    # Create a combined seed from admin_password + seed
    combined_seed = admin_password + seed

    # Set the random seed for deterministic behavior
    random.seed(combined_seed)

    # Choose your password components
    alphabet = string.ascii_letters + string.digits

    # Build a deterministic password of desired length
    password = ''.join(random.choice(alphabet) for _ in range(length))

    return password
