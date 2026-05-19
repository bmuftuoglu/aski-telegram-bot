import os
import tempfile

os.environ.setdefault("ASKI_TARGET_DISTRICT", "ÇANKAYA")
os.environ.setdefault("ASKI_TARGET_NEIGHBORHOOD", "Test Mahallesi")
os.environ.setdefault("INTERNAL_API_TOKEN", "test-token-123")
os.environ.setdefault("GATEWAY_NOTIFY_URL", "http://localhost:8080/notify")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
