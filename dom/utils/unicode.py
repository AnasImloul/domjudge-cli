import re
import unicodedata

def clean_team_name(team_name: str, allow_spaces: bool = True) -> str:
    # Normalize accents and special letters
    team_name = unicodedata.normalize('NFKD', team_name)
    team_name = team_name.encode('ascii', 'ignore').decode('ascii')

    # Replace forbidden characters with a space
    team_name = re.sub(r'[^a-zA-Z0-9_\-@.]', ' ' if allow_spaces else "_", team_name)

    # Collapse multiple spaces into a single space
    team_name = re.sub(r'\s+', ' ', team_name)

    # Strip leading/trailing spaces
    team_name = team_name.strip()

    return team_name if allow_spaces else team_name.replace(" ", "")
