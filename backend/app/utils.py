import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "test-key"))


def critique_allowed(text: str) -> bool:
    """
    True if critique is allowed (non-toxic etc.). Fail-open on errors.
    """
    try:
        res = client.moderations.create(
            model="omni-moderation-latest",
            input=text
        )
        return not res.results[0].flagged
    except Exception as exc:
        # keep UX smooth; log to stderr
        print("moderation error – allowing text:", exc)
        return True
