from asyncio import run
from json import dumps as json_dumps
from json import loads as json_loads
from os import environ

import logfire
from dotenv import load_dotenv
from httpx2 import AsyncClient

from .agent import Deps, get_agent, read_history, write_history
from .mattermost import get_user, get_users_and_members


async def arun(mattermost_base_url: str, mattermost_token: str) -> None:
    agent = get_agent()

    async with AsyncClient(
        base_url=mattermost_base_url + "/api/v4",
        headers={"Authorization": f"Bearer {mattermost_token}"},
    ) as client:
        # Example request, replace with actual logic
        me_data = await get_user(client, "me")
        me_id = me_data["id"]
        me_name = me_data["username"]
        me_first_name = me_data["first_name"]

        users, channel_members = await get_users_and_members(client, me_id)

        async with client.websocket("/websocket") as ws:
            while True:
                msg = await ws.receive_json()
                if msg["event"] != "posted":
                    continue

                event_data = msg["data"]
                post_data = json_loads(event_data["post"])

                message = post_data["message"]
                if (
                    not "@" + me_name in message
                ):  # Ignore messages that do not mention the bot
                    continue

                channel_id = post_data["channel_id"]
                thread_id = post_data["root_id"] or post_data["id"]

                # Build the list of users in the current channel
                users_in_channel = [
                    users[user_id] for user_id in channel_members[channel_id]
                ]

                # Build the dependencies for the agent
                deps = Deps(
                    me_name=me_first_name,
                    users=users_in_channel,
                )

                # Load the conversation history for the current thread
                history = await read_history(channel_id, thread_id)

                # Build the prompt for the agent
                prompt = json_dumps(
                    {
                        "user": users[post_data["user_id"]]["username"],
                        "message": message,
                    }
                )

                # Run the agent with the constructed prompt and dependencies
                r = await agent.run(
                    prompt,
                    deps=deps,
                    message_history=history,
                )

                # Send the agent's response as a reply in the current thread
                await client.post(
                    "/posts",
                    json={
                        "channel_id": channel_id,
                        "root_id": thread_id,
                        "message": r.output,
                    },
                )

                # Save the updated conversation history for the current thread
                await write_history(channel_id, thread_id, r.all_messages())


def main() -> None:
    load_dotenv()

    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_httpx()
    logfire.instrument_pydantic_ai()

    mattermost_base_url = environ["MATTERMOST_BASE_URL"]
    mattermost_token = environ["MATTERMOST_TOKEN"]

    run(arun(mattermost_base_url, mattermost_token))
