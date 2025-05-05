import os
from mistralai import Mistral

# Make sure this prints the key
print("🔐 Loaded MISTRAL API KEY:", os.getenv("MISTRALAI_API_KEY"))

client = Mistral(api_key=os.getenv("MISTRALAI_API_KEY"))

# Try any harmless call (listing files, etc.)
try:
    response = client.files.list()
    print("✅ Mistral API is accessible. File list:")
    print(response)
except Exception as e:
    print("❌ Error reaching Mistral API:")
    print(e)
