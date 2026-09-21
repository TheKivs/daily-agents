import os
import requests
import feedparser  # pip install feedparser google-genai
from google import genai

# Configuration
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TARGET_CARDS = [
    "American Express Platinum",
    "Capital One Venture X",
    "Amex Blue Cash Everyday",
    "Chase Sapphire Reserve"
]

def fetch_latest_card_news() -> str:
    """Fetches recent credit card deal headlines and summaries from RSS feeds."""
    feed = feedparser.parse("https://www.doctorofcredit.com/category/credit-cards/feed/")
    news_items = []
    
    for entry in feed.entries[:15]:
        title = entry.title
        summary = entry.summary if "summary" in entry else ""
        if any(card.lower() in (title + summary).lower() for card in TARGET_CARDS) or "transfer bonus" in title.lower():
            news_items.append(f"Title: {title}\nDetails: {summary[:300]}...\n")
            
    return "\n---\n".join(news_items) if news_items else "No specific target card updates found today."

def evaluate_offers_with_ai(raw_news: str) -> str:
    """Uses Gemini to filter and format card deals into a strict short layout."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Analyze the following credit card updates ONLY for these exact cards: {", ".join(TARGET_CARDS)}.
    Strictly ignore any offers for cards not in this list.

    RAW DATA:
    {raw_news}

    INSTRUCTIONS:
    1. Filter out routine perks. Include ONLY high-value deals (e.g., transfer bonuses, notable US travel deals, major dining credits). 
    No new cardholder offers needed.
    2. Format EACH matching offer strictly using this template (no extra text or bullet points):
    - Card: [Card Name]
    - Offer: [4-5 words]
    - Deal expires: [date, if available, else skip]
    - Detail: [1 line summary]
    - Offer quality: [A+, A, B+, B, B-, etc]

    3. Separate multiple offers with a single blank line.
    4. If no exceptional offers exist for a particular card, just don't print anything.
    5. If no exceptional offers exist for ANY of these cards, respond with EXACTLY 'NO_DEALS'. 
    """

    chat = client.chats.create(model="gemini-3-flash-preview")
    response = chat.send_message(prompt)

    return response.text.strip()

def send_discord_alert(content: str):
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable is missing!")
        return

    if content != "NO_DEALS":
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
        if response.status_code == 204:
            print("Successfully posted to Discord!")
        else:
            print(
                f"Discord API error {response.status_code}: {response.text}"
            )

if __name__ == "__main__":
    print("Fetching card news...")
    raw_data = fetch_latest_card_news()
    print(f"DEBUG: Fetched raw news length: {len(raw_data)} chars")

    print("Evaluating with AI...")
    ai_verdict = evaluate_offers_with_ai(raw_data)
    print(f"DEBUG AI Verdict:\n{ai_verdict}\n")

    send_discord_alert(f"💳 **Credit Card Offer AI Intelligence**\n\n{ai_verdict}")