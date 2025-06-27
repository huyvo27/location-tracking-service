import random
import secrets
import string


def random_lower_string(length: int = 24) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def generate_strong_password(length: int = 16) -> str:
    if length < 8:
        raise Exception("Length should greater than 8 characters")
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "@$!%*?&"

    all_chars = uppercase + lowercase + digits + special

    password = []
    password.append(secrets.choice(uppercase))
    password.append(secrets.choice(lowercase))
    password.append(secrets.choice(digits))
    password.append(secrets.choice(special))

    remaining_length = length - len(password)

    for _ in range(remaining_length):
        password.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(password)

    return "".join(password)


def generate_phone_number(international: bool = False, length: int = None) -> str:
    if international:
        min_length, max_length = 10, 15
    else:
        min_length, max_length = 9, 10

    if length is None:
        length = secrets.randbelow(max_length - min_length + 1) + min_length
    elif not (min_length <= length <= max_length):
        raise ValueError(
            f"Length must be between {min_length} and {max_length} for "
            f"{'international' if international else 'local'} format"
        )

    digits = "".join(secrets.choice(string.digits) for _ in range(length))

    if international:
        prefix = "+" if secrets.randbelow(2) == 0 else ""
        return f"{prefix}{digits}"
    else:
        return f"0{digits}"
