"""Explicit development reset. Never called by normal startup."""

import os
import sys
from sqlalchemy import text
from apps.api.app.store import engine, migrate, seed, seed_warranty_examples, seed_metadata

if "--confirm-demo-reset" not in sys.argv or os.getenv("DEMO_MODE", "true") != "true":
    raise SystemExit("Use --confirm-demo-reset with DEMO_MODE=true. This deletes all demo records.")
migrate()
with engine.begin() as c:
    c.execute(text("DELETE FROM records"))
    c.execute(text("DELETE FROM public_tokens"))
    c.execute(text("DELETE FROM rate_limits"))
seed()
seed_warranty_examples()
seed_metadata()
print("Demo database reset to 26 synthetic vehicles. Upload files are retained.")
