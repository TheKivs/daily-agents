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
    "American Express Delta SkyMiles Gold Card",
    "Chase Sapphire Reserve",
    "Bank of America® Customized Cash Rewards",
    "Chase Freedom Unlimited",
    "American Express Blue Cash Everyday"
]

RSS_FEEDS = [
    "https://www.doctorofcredit.com/feed/",
    "https://www.uscreditcardguide.com/en/feed/",
    "https://frequentmiler.com/feed/",
]

def fetch_latest_card_news() -> str:
    """Fetches and merges recent card news from multiple top industry feeds."""
    news_items = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:  # Grab latest 20 per feed
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')
                text_block = f"{title} {summary}".lower()
                
                # Check for target cards or high-value triggers
                if any(card.lower() in text_block for card in TARGET_CARDS) or "transfer bonus" in text_block:
                    news_items.append(f"Source: {feed_url}\nTitle: {title}\nSummary: {summary[:1000]}...\n")
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")

    return "\n---\n".join(news_items) if news_items else "No relevant card updates found."

def fetch_gemini_model(client):
    print("Testing available text models...\n")
    prompt = "How many elements in the periodic table?"

    try:
        for model in client.models.list():
            # Check capabilities BEFORE printing or calling
            supported_actions = getattr(model, "supported_actions", [])
            if "generateContent" not in supported_actions:
                continue

            print(f"Testing: {model.name}")
            try:
                response = client.models.generate_content(
                    model=model.name,
                    contents=prompt
                )
                if response and response.text:
                    print(f"Successfully selected model: {model.name}\n")
                    return model.name
            except Exception as e:
                # Log error and CONTINUE to the next model in the list
                continue

    except Exception as e:
        print(f"Failed to fetch model list: {e}")

    # Explicit fallback if loop completes with no working models
    return None

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
    2. Summarize medium or high-value deals (e.g., airline/hotel transfer bonuses, notable hotels/travel deals, major dining credits, shopping, etc.). Exclude new cardholder deals.
    3. Format EACH matching offer strictly using this template (no extra text or bullet points):
    - Card: [Card Name]
    - Offer: [4-5 words]
    - Deal expires: [date, if available, else skip]
    - Detail: [1 line summary]
    - Offer quality: [A+, A, B+, B, B-, etc]

    4. Separate multiple offers with a single blank line.
    5. If no exceptional offers exist for a particular card, just don't print anything. If no exceptional offers exist for ANY of these cards, respond with EXACTLY 'NO_DEALS'. 
    """
    MODEL = fetch_gemini_model(client)
    chat = client.chats.create(model=MODEL)
    response = chat.send_message(prompt)
    verdict = response.text.strip()

    if verdict != "NO_DEALS":
        return f"{verdict}\n*Powered by Gemini/{MODEL.split("/")[1]}*\n"
    return f"No Deals on {date.today()}"

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

    send_discord_alert(f"🚀 **Credit Card Offers AI Digest**\n\n{ai_verdict}")