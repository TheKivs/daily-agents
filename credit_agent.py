import os
import requests
import feedparser 
from google import genai
from datetime import date

# Configuration
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TARGET_CARDS = [
    "American Express Platinum",
    "Capital One Venture X",
    "American Express Delta SkyMiles® Gold Card",
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
    Analyze the following credit card offerings updates ONLY for these cards: {", ".join(TARGET_CARDS)}.
    Strictly ignore any offers for cards not in this list.
    Ensure these are updated and relevant to the current date. 

    RAW DATA: As of {date.today()}:
    {raw_news}

    INSTRUCTIONS:
    1. If card annual fees have changed, add that at the beginning.
    2. Summarize high-value deals (e.g., airline/hotel transfer bonuses, notable hotels/travel deals, major dining credits). 
    No new cardholder offers needed.
    3. Format EACH matching offer strictly using this template (no extra text or bullet points):
    - Card: [Card Name]
    - Offer: [4-5 words]
    - Deal expires: [date, if available, else skip]
    - Detail: [1 line summary]
    - Offer quality: [A+, A, B+, B, B-, etc]

    4. Separate multiple offers with a single blank line.
    5. If no exceptional offers exist for a particular card, just don't print anything. If no exceptional offers exist for ANY of these cards, respond with EXACTLY 'NO_DEALS'. 
    """

    chat = client.chats.create(model="gemini-3-flash-preview", tier="free")
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
    print("Working on card data...")
    raw_data = fetch_latest_card_news()
    ai_verdict = evaluate_offers_with_ai(raw_data)
    print(f"DEBUG AI Verdict:\n{ai_verdict}\n")

    send_discord_alert(f"💳 **Credit Card Offer AI Intelligence**\n\n{ai_verdict}")