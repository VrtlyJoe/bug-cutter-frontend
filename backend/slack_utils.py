import os, requests, json

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")      # xoxb- token
SLACK_CHANNEL   = os.getenv("SLACK_CHANNEL_ID")     # e.g. C0123456789

def send_slack_notification(issue_key, summary, priority, category, reporter, image_urls):

    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
        print("⚠️  Slack env vars not set.")
        return

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New Bug:* <https://vrtlyai.atlassian.net/browse/{issue_key}|{issue_key}> – {summary}"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type":"mrkdwn","text":f"*Priority:* {priority}"},
                {"type":"mrkdwn","text":f"*Category:* {category}"},
                {"type":"mrkdwn","text":f"*Reporter:* {reporter}"},
            ]
        },
    ]

    if image_urls:
        blocks.append({
            "type":"image",
            "image_url":image_urls[0],
            "alt_text":"screenshot"
        })

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type":  "application/json; charset=utf-8",
    }
    body = {"channel": SLACK_CHANNEL, "blocks": blocks}

    r = requests.post("https://slack.com/api/chat.postMessage",
                      headers=headers, data=json.dumps(body))
    if not r.ok or not r.json().get("ok"):
        print("❌ Slack error:", r.text)
    else:
        print("✅ Slack message sent")
