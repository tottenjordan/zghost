import os
from dotenv import load_dotenv

dotenv_path = os.path.join(
    os.path.dirname(__file__), "../trends_and_insights_agent/.env"
)
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # error:
    print("no .env file found")
    raise (FileNotFoundError, "no .env file found")

