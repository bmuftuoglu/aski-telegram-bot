import os

# Set required env vars before any app module is imported during test collection.
os.environ.setdefault("TARGET_DISTRICT", "ÇANKAYA")
os.environ.setdefault("TARGET_NEIGHBORHOOD", "Test Mahallesi")
