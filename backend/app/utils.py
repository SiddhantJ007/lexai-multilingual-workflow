from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI()  # picks up OPENAI_API_KEY

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
