"""Show all accounts and their URLs"""

from backend.services.database import SessionLocal
from backend.models import Account

db = SessionLocal()
accounts = db.query(Account).all()

print("\nAll Accounts:\n")
for account in sorted(accounts, key=lambda a: a.name):
    print(f"{account.name:30} {account.url}")
print()
