from asyncio import run
from dataclasses import dataclass
from json import dumps as json_dumps
from json import loads as json_loads
from os import environ
from typing import cast

import logfire
from aiofiles import open as aopen
from aiofiles.os import replace as areplace
from dotenv import load_dotenv
from httpx2 import AsyncClient
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessagesTypeAdapter


@dataclass
class Deps:
    me_name: str
    users: list[dict]


def system_prompt(ctx: RunContext[Deps]) -> str:
    deps = ctx.deps
    me_name = deps.me_name
    users = deps.users

    p = f"""\
Tu es {me_name}, le maitre du jeu sur un channel Mattermost de jeu de role.
L'univers est de jeu est Shadowrun.
Le système de jeu est quasi exclusivement narratif.
Pas vraiment de règles ou de mécanismes stricts, l'accent est mis sur la narration.

Les joueurs sont :
```jsonl
"""

    for user_data in users:
        p += f"{json_dumps(user_data)}\n"
    p += "```"

    return p


async def get_json(client: AsyncClient, url: str) -> dict | list:
    return (await client.get(url)).json()


async def get_user(client: AsyncClient, u_id: str) -> dict:
    user = cast(dict, await get_json(client, f"/users/{u_id}"))

    return {
        "id": user["id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "nickname": user["nickname"],
    }


async def get_channels_for_user(client: AsyncClient, user_id: str) -> list[str]:
    memberships = await get_json(client, f"/users/{user_id}/channels")

    return [m["id"] for m in memberships]


async def get_channel_members(
    client: AsyncClient, channel_id: str, me_id: str
) -> list[str]:
    members = await get_json(client, f"/channels/{channel_id}/members")
    return [m["user_id"] for m in members if m["user_id"] != me_id]


async def get_users_and_members(
    client: AsyncClient, me_id: str
) -> tuple[dict[str, dict], dict[str, list[str]]]:

    users: dict[str, dict] = {}
    channel_members: dict[str, list[str]] = {}

    for channel_id in await get_channels_for_user(client, me_id):
        members = await get_channel_members(client, channel_id, me_id)
        channel_members[channel_id] = members

        for user_id in members:
            if user_id not in users:
                users[user_id] = await get_user(client, user_id)

    return users, channel_members


async def arun(mattermost_base_url: str, mattermost_token: str) -> None:
    agent = Agent(model="google:gemini-3.5-flash-lite", deps_type=Deps)
    agent.system_prompt()(system_prompt)

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
                if msg["event"] == "posted":
                    event_data = msg["data"]
                    post_data = json_loads(event_data["post"])
                    if post_data["root_id"]:
                        continue

                    post_message = post_data["message"]
                    if not "@" + me_name in post_message:
                        continue

                    channel_id = post_data["channel_id"]
                    users_in_channel = [
                        users[user_id] for user_id in channel_members[channel_id]
                    ]
                    deps = Deps(
                        me_name=me_first_name,
                        users=users_in_channel,
                    )

                    history_name = f"history_{channel_id}.json"
                    try:
                        async with aopen(history_name, "rb") as f:
                            history = ModelMessagesTypeAdapter.validate_json(
                                await f.read()
                            )
                    except FileNotFoundError:
                        history = []

                    prompt = json_dumps(
                        {
                            "user": users[post_data["user_id"]]["username"],
                            "message": post_message,
                        }
                    )
                    r = await agent.run(
                        prompt,
                        deps=deps,
                        message_history=history,
                    )
                    await client.post(
                        "/posts",
                        json={
                            "channel_id": channel_id,
                            "message": r.output,
                        },
                    )

                    tmp_history_name = f"tmp_{history_name}"
                    async with aopen(tmp_history_name, "wb") as f:
                        await f.write(
                            ModelMessagesTypeAdapter.dump_json(
                                r.all_messages(), indent=2
                            )
                        )
                    await areplace(tmp_history_name, history_name)


def main() -> None:
    load_dotenv()

    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_httpx()
    logfire.instrument_pydantic_ai()

    mattermost_base_url = environ["MATTERMOST_BASE_URL"]
    mattermost_token = environ["MATTERMOST_TOKEN"]

    run(arun(mattermost_base_url, mattermost_token))
