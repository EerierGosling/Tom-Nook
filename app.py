import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import random

load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

channel_id = "C06V73WGACB"
shop_id = "C08C5TPLWTD"

threads = {}

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://tools.slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html

@app.event("member_joined_channel")
def welcome(event, say):
    channel = event["channel"]

    if channel not in [channel_id, shop_id]:
        print("not the right channel")
        print(channel)
        return
    
    start_shop(say, event["channel"], event["user"])

@app.action("button_click")
def open_modal(ack, body, client):
    # Acknowledge the command request

    ts = body["message"]["ts"]

    user_id = threads[ts]["user"]

    clicked_user_id = body["user"]["id"]

    if user_id != clicked_user_id:
        ack()
        client.chat_postEphemeral(
            channel = channel_id,
            user = clicked_user_id,
            text = f"you aren't <@{user_id}>! you can't buy stuff for them!"
        )
        ack()
        return

    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "item_modal",
            "private_metadata": body["message"]["ts"],
            "title": {
                "type": "plain_text",
                "text": "Tom Nook's Store",
                "emoji": True
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit",
                "emoji": True
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "item_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "item_input"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "what do you want to buy?",
                        "emoji": True
                    }
                }
            ]
        }
    )

@app.view("item_modal")
def handle_item_submission(ack, body, client, view, logger):

    item = view["state"]["values"]["item_block"]["item_input"]["value"]
    ts = body["view"]["private_metadata"]

    user_id = threads[ts]["user"]

    if threads[ts]["channel"] == channel_id:
        text = f"welcome <@{user_id}>!\n\ngimme all your hard-earned bells :acnh_bells_100::ac-bells: and i’ll sell you something you (might) want\n\n<@{user_id}> clicked *buy stuff (this is mandatory.)*"
    else:
        text = f"hello <@{user_id}>!\n\ngimme all your hard-earned bells :acnh_bells_100::ac-bells: and i’ll sell you something you (might) want\n\n<@{user_id}> clicked *buy stuff (this is mandatory.)*"

    client.chat_update(
        channel=threads[ts]["channel"],
        ts=body["view"]["private_metadata"],
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ],
        text=text
    )

    threads[ts]["item"] = item

    ack()

    client.chat_postMessage(
        channel=threads[ts]["channel"],
        thread_ts=ts,
        text=f"sure, i’ll sell you a `{threads[ts]['item']}`! that’ll be...... {threads[ts]['cost']} bells. pay up! :grin:"
    )
    client.chat_postMessage(
        channel=threads[ts]["channel"],
        thread_ts=ts,
        text=f"replying with :ac-bells: (1,000) and :acnh_bells_100: (100) will suffice - send enough to add up to {threads[ts]['cost']} :grin::grin::grin::grin:"
    )
    ack()

@app.event("message")
def message_pay(message, say):

    if message["channel"] == shop_id:
        start_shop(say, message["channel"], message["user"])

    if "thread_ts" not in message:
        return
    
    ts = message["thread_ts"]
    if ts not in threads:
        return
    
    if message["user"] != threads[ts]["user"]:
        return
    
    if threads[ts]["item"] is None:
        return
    
    content = message["text"]
    
    threads[ts]["spent"] += content.count(":ac-bells:")*1000 + content.count(":acnh_bells_100:")*100

    spent = threads[ts]["spent"]
    cost = threads[ts]["cost"]
    item = threads[ts]["item"]

    if spent < cost:
        say(
            channel=threads[ts]["channel"],
            thread_ts=ts,
            text=f"you’ve spent {spent} bells so far - keep going! i need {cost} bells :grin:"
        )

    elif spent > cost:
        say(
            channel=threads[ts]["channel"],
            thread_ts=ts,
            text=f"here's your `{item}`! _thanks for the extra {spent-cost} bells..._"
        )
        threads.pop(ts)

    else:
        say(
            channel=threads[ts]["channel"],
            thread_ts=ts,
            text=f"here's your `{item}`! thanks for the purchase! :grin:"
        )
        threads.pop(ts)

@app.command("/tom-nook")
def slash_command(req, ctx):
    start_shop(ctx["say"], ctx["channel_id"], ctx["user_id"])

def start_shop(say, channel, user_id):

    if channel == channel_id:
        text = f"welcome <@{user_id}>!\n\ngimme all your hard-earned bells :acnh_bells_100::ac-bells: and i’ll sell you something you (might) want"
    else:
        text = f"hello <@{user_id}>!\n\ngimme all your hard-earned bells :acnh_bells_100::ac-bells: and i’ll sell you something you (might) want"

    response = say(
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "style": "primary",
                        "text": {
                            "type": "plain_text",
                            "text": "buy something.",
                            "emoji": True
                        },
                        "action_id": "button_click"
                    }
                ]
            }
        ],
        text=text
    )

    if response["message"]["ts"] not in threads:
        threads[response["message"]["ts"]] = { "channel": channel, "user": user_id, "item": None, "spent": 0, "cost": random.randint(1, 100)*100 }

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()