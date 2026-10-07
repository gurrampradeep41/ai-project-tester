import os
import sys

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


print()
print("=" * 46)
print("          GROQ API CONNECTION TEST")
print("=" * 46)


api_key = os.getenv(
    "GROQ_API_KEY"
)

model = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


# ---------------------------------------------------------
# API KEY
# ---------------------------------------------------------

if not api_key:
    print("❌ GROQ_API_KEY")
    print("   API key not found in .env")
    sys.exit(1)

print("✅ GROQ_API_KEY")
print("   API key detected.")


# ---------------------------------------------------------
# MODEL
# ---------------------------------------------------------

print("✅ Groq model")
print(f"   {model}")


# ---------------------------------------------------------
# CLIENT
# ---------------------------------------------------------

try:
    client = Groq(
        api_key=api_key
    )

    print("✅ Groq client")
    print(
        "   Client initialized successfully."
    )

except Exception as exc:
    print("❌ Groq client")
    print(f"   {exc}")
    sys.exit(1)


# ---------------------------------------------------------
# BASIC API TEST
# ---------------------------------------------------------

print()
print("Testing Groq API...")

try:

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Reply with exactly: "
                    "GROQ CONNECTION SUCCESS"
                ),
            }
        ],
        temperature=0,
        max_completion_tokens=50,
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    print("✅ Groq API request")
    print(
        f"   Response: {content}"
    )

except Exception as exc:
    print("❌ Groq API request")
    print(f"   {exc}")
    sys.exit(1)


# ---------------------------------------------------------
# JSON TEST
# ---------------------------------------------------------

print()
print("Testing JSON response mode...")

try:

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    'Return {"status":"success"}'
                ),
            },
        ],
        temperature=0,
        max_completion_tokens=100,
        response_format={
            "type": "json_object"
        },
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    print("✅ JSON response mode")
    print(
        f"   Response: {content}"
    )

except Exception as exc:
    print("❌ JSON response mode")
    print(f"   {exc}")
    sys.exit(1)


print()
print("=" * 46)
print("          GROQ TEST PASSED")
print("=" * 46)
print()