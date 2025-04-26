import bcrypt


def generate_bcrypt_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=5)  # rounds=5 to match htpasswd -B behavior
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')
