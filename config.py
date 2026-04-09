import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get API key from environment
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

ALLOWED_INTENTS = ["refund", "return", "exchange"]

CONFIDENCE_THRESHOLD = 0.8

# Safety rule
STRICT_REFUND_POLICY = True
    