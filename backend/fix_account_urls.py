"""Fix account URLs — replace app.orcanos.com with us.orcanos.com"""

from backend.services.database import SessionLocal
from backend.models import Account

db = SessionLocal()

accounts = db.query(Account).all()
updated = 0

for account in accounts:
    if "app.orcanos.com" in account.url:
        old_url = account.url
        account.url = account.url.replace("app.orcanos.com", "us.orcanos.com")
        print(f"Updated {account.name}: {old_url} -> {account.url}")
        updated += 1

db.commit()
print(f"\nFixed {updated} account(s)")
