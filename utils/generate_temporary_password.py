import secrets
import string

def generate_temporary_password(length=12):
    """
    Generate a random password with at least one uppercase, one lowercase, one digit, and one special character.
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    alphabet = string.ascii_letters
    digits = string.digits
    special_characters = "!@#$%^&*()-_+=<>?/"

    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(digits),
        secrets.choice(special_characters),
    ]

    remaining_length = length - len(password)
    password += [secrets.choice(alphabet + digits + special_characters) for _ in range(remaining_length)]

    secrets.SystemRandom().shuffle(password)
    return ''.join(password)