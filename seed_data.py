# backend/app/seed_data.py
"""
Seed script to populate the database with test data.
Creates users and addresses
"""

import asyncio
import random

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.logger import (
    console,
    log_panel,
    log_progress,
    log_section,
    log_table,
)
from app.core.security import get_password_hash
from app.models.models import (
    Address,
    User,
    UserRole,
)

COUNTIES = [
    "Nairobi",
    "Mombasa",
    "Kisumu",
    "Nakuru",
    "Eldoret",
    "Thika",
    "Malindi",
    "Kitale",
    "Garissa",
    "Kakamega",
]

FIRST_NAMES = [
    "Wanjiku",
    "Kamau",
    "Achieng",
    "Omondi",
    "Njeri",
    "Mwangi",
    "Akinyi",
    "Kipchoge",
    "Wambui",
    "Otieno",
    "Nyambura",
    "Kariuki",
    "Chebet",
    "Mutua",
    "Wairimu",
]

LAST_NAMES = [
    "Kimani",
    "Odhiambo",
    "Kiplagat",
    "Mwangi",
    "Onyango",
    "Koech",
    "Wanjiru",
    "Ngugi",
    "Juma",
    "Kamau",
    "Rotich",
    "Ndung'u",
    "Ochieng",
    "Maina",
    "Cheruiyot",
]


async def create_users(session, count: int = 10):
    """Create test users with different roles"""
    console.print(f"\n[cyan]👥 Creating {count} users...[/cyan]")

    users = []

    with log_progress() as progress:
        task = progress.add_task("[cyan]Creating users...", total=count)

        # Create admin user
        admin = User(
            email=settings.ADMIN,
            full_name="Admin User",
            phone_number="1234567890",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        users.append(admin)
        progress.update(task, advance=1)
        console.print(f"  [green]✓[/green] Created admin: {admin.email}")

        # Create staff users
        for i in range(4):
            staff = User(
                email=f"staff{i + 1}@restaurant.co.ke",
                full_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                phone_number=f"07{random.randint(10000000, 99999999)}",
                hashed_password=get_password_hash("password123"),
                role=UserRole.STAFF,
                is_active=True,
                is_verified=True,
            )
            session.add(staff)
            users.append(staff)
            progress.update(task, advance=1)
            console.print(f"  [green]✓[/green] Created staff: {staff.email}")

        # Create regular customers
        for i in range(count - 5):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            customer = User(
                email=f"{first_name.lower()}.{last_name.lower()}{i}@gmail.com",
                full_name=f"{first_name} {last_name}",
                phone_number=f"07{random.randint(10000000, 99999999)}",
                hashed_password=get_password_hash("password123"),
                role=UserRole.CUSTOMER,
                is_active=True,
                is_verified=random.choice([True, False]),
            )
            session.add(customer)
            users.append(customer)
            progress.update(task, advance=1)

    await session.commit()
    for user in users:
        await session.refresh(user)

    # Show summary table
    user_summary = []
    role_counts = {}
    for user in users:
        role_counts[user.role] = role_counts.get(user.role, 0) + 1

    for role, count in role_counts.items():
        user_summary.append(
            {
                "role": role,
                "count": count,
                "verified": sum(1 for u in users if u.role == role and u.is_verified),
            }
        )

    console.print()
    log_table(user_summary, title="Users Created", show_lines=True)

    return users


async def create_addresses(session, users):
    """Create addresses for users"""
    console.print("\n[cyan]🏠 Creating addresses...[/cyan]")

    addresses = []
    customer_users = [u for u in users if u.role == UserRole.CUSTOMER]
    total_addresses = sum(random.randint(2, 3) for _ in customer_users)

    with log_progress() as progress:
        task = progress.add_task("[cyan]Creating addresses...", total=total_addresses)

        for user in customer_users:
            num_addresses = random.randint(2, 3)
            for i in range(num_addresses):
                county = random.choice(COUNTIES)
                address = Address(
                    owner_id=user.id,
                    street_address=f"{random.randint(1, 999)} {random.choice(['Moi', 'Kenyatta', 'Uhuru', 'Kimathi', 'Ngong'])} Avenue",
                    apartment=f"Apt {random.randint(1, 50)}"
                    if random.choice([True, False])
                    else None,
                    city=county,
                    county=county,
                    postal_code=f"{random.randint(10000, 99999)}",
                    is_default=(i == 0),
                    delivery_instructions=random.choice(
                        [
                            "Ring the doorbell twice",
                            "Call when you arrive",
                            "Leave at the gate",
                            None,
                        ]
                    ),
                )
                session.add(address)
                addresses.append(address)
                progress.update(task, advance=1)

    await session.commit()
    for addr in addresses:
        await session.refresh(addr)

    # Show addresses by county
    county_counts = {}
    for addr in addresses:
        county_counts[addr.county] = county_counts.get(addr.county, 0) + 1

    county_data = [{"county": k, "addresses": v} for k, v in sorted(county_counts.items())]
    console.print()
    log_table(county_data, title="Addresses by County", show_lines=True)

    return addresses


async def seed_database():
    """Main function to seed all data"""
    log_section("🌱 DATABASE SEEDING", "bold green")

    async with AsyncSessionLocal() as session:
        try:
            # Create all data in order
            users = await create_users(session, count=15)
            addresses = await create_addresses(session, users)

            # Display beautiful summary
            console.print()
            log_section("✨ SEEDING COMPLETED", "bold green")

            summary_text = f"""
[bold cyan]Database Summary[/bold cyan]

[yellow]Users Created:[/yellow]
  • Total: {len(users)}
  • Admins: {sum(1 for u in users if u.role == UserRole.ADMIN)}
  • Staff: {sum(1 for u in users if u.role == UserRole.STAFF)}
  • Customers: {sum(1 for u in users if u.role == UserRole.CUSTOMER)}

[yellow]Addresses Created:[/yellow]
  • Total: {len(addresses)}
  • Default addresses: {sum(1 for a in addresses if a.is_default)}

[yellow]Test Credentials:[/yellow]
  • [bold]Admin:[/bold] {settings.ADMIN} / {settings.ADMIN_PASSWORD}
  • [bold]Staff:[/bold] staff1@restaurant.co.ke / password123
  • [bold]Customer:[/bold] (any customer email) / password123
            """

            log_panel(message=summary_text, title="🎉 Seeding Complete", style="success")

        except Exception as e:
            console.print(f"\n[bold red] Error during seeding:[/bold red] {e}")
            await session.rollback()
            raise


async def seed_all_data():
    """Alias for backward compatibility"""
    await seed_database()


if __name__ == "__main__":
    asyncio.run(seed_database())
