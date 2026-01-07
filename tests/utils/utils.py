# tests/utils/utils.py
import random
import string

from httpx import AsyncClient

from app.core.config import settings


def random_lower_string(length: int = 32) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email address."""
    return f"{random_lower_string()}@example.com"


def random_phone_number() -> str:
    """
    Generate a realistic Kenyan phone number.
    Valid formats:
      - 07XX XXX XXX
      - 01XX XXX XXX
    """
    valid_prefixes = [
        "070",
        "071",
        "072",
        "073",
        "074",
        "075",
        "076",
        "077",
        "078",
        "079",
        "010",
        "011",
        "012",
    ]
    prefix = random.choice(valid_prefixes)
    remaining_digits = "".join(random.choices("0123456789", k=6))
    return prefix + remaining_digits


async def get_admin_token_headers(client: AsyncClient) -> dict[str, str]:
    """Get authentication headers for superuser."""
    login_data = {
        "username": settings.ADMIN,
        "password": settings.ADMIN_PASSWORD,
    }
    r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)

    if r.status_code != 200:
        raise Exception(f"Login failed: {r.status_code} - {r.text}")

    response_data = r.json()
    a_token = response_data["access_token"]
    return {"Authorization": f"Bearer {a_token}"}
