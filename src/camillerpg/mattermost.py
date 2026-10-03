# CamilleRPG - An AI assistant
# Copyright (C) Jonathan Tremesaygues <jonathan@tremesaygues.eu>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
from argparse import ArgumentParser, Namespace
from asyncio import gather
from collections.abc import Iterable
from dataclasses import dataclass
from json import dumps as json_dumps
from json import loads as json_loads
from os import environ
from types import TracebackType
from typing import Self, cast

from httpx2 import AsyncClient
from httpx2.websockets import AsyncWebSocketSession

from .ai import CamilleAgent, Deps, User


@dataclass
class MattermostUser(User):
    id: str
    username: str
    first_name: str | None
    last_name: str | None
    nickname: str | None


class MattermostAgent(CamilleAgent):
    def __init__(self, base_url: str, token: str) -> None:
        super().__init__()

        self.client = AsyncClient(
            base_url=base_url + "/api/v4", headers={"Authorization": "Bearer " + token}
        )
        self.ws_seq = 0

    async def __aenter__(self) -> Self:
        await self.client.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.client.aclose()

    async def get_json(self, endpoint: str) -> dict | list:
        response = await self.client.get(endpoint)
        response.raise_for_status()

        return response.json()

    async def get_user(self, user_id: str) -> MattermostUser:
        data = cast(dict, await self.get_json(f"/users/{user_id}"))

        return MattermostUser(
            id=data["id"],
            username=data["username"],
            first_name=data.get("first_name") or None,
            last_name=data.get("last_name") or None,
            nickname=data.get("nickname") or None,
        )

    async def get_channels_for_user(self, user_id: str) -> list[str]:
        return [
            m["id"]
            for m in cast(list, await self.get_json(f"/users/{user_id}/channels"))
        ]

    async def get_channel_members(self, channel_id: str, me_id: str) -> list[str]:
        return [
            m["user_id"]
            for m in cast(list, await self.get_json(f"/channels/{channel_id}/members"))
            if m["user_id"] != me_id
        ]

    async def get_channels_members(self, me_id: str) -> dict[str, list[str]]:
        channels = await self.get_channels_for_user(me_id)
        return {
            channel_id: await self.get_channel_members(channel_id, me_id)
            for channel_id in channels
        }

    async def get_users(self, user_ids: Iterable[str]) -> dict[str, MattermostUser]:
        user_ids = set(user_ids)
        return {
            user_id: user
            for user_id, user in zip(
                user_ids,
                await gather(*(self.get_user(user_id) for user_id in user_ids)),
            )
        }

    async def get_channels_users(
        self, me_id: str
    ) -> tuple[dict[str, MattermostUser], dict[str, list[MattermostUser]]]:
        channels_members_ids = await self.get_channels_members(me_id)
        users = await self.get_users(
            user_id
            for user_ids in channels_members_ids.values()
            for user_id in user_ids
        )
        channels_users = {
            channel_id: [users[user_id] for user_id in user_ids]
            for channel_id, user_ids in channels_members_ids.items()
        }

        return users, channels_users

    async def arun(self) -> None:
        # Fetch the current user's information, the channels they are members of, and the users in those channels
        me = await self.get_user("me")
        me_mention = "@" + me.username
        users, channels_users = await self.get_channels_users(me.id)

        # Connect to the Mattermost WebSocket
        async with self.client.websocket("/websocket") as ws:
            while True:
                msg = await ws.receive_json()
                if msg.get("event") != "posted":
                    continue

                event_data = msg["data"]
                post_data = json_loads(event_data["post"])

                message = post_data["message"]
                if (
                    not me_mention in message
                ):  # Ignore messages that do not mention the bot
                    continue

                channel_id = post_data["channel_id"]
                post_id = post_data["id"]
                root_id = post_data["root_id"] or None
                thread_id = root_id or post_id

                # Build the dependencies for the agent
                deps = Deps(
                    me_name=me.username,
                    users=cast(list[User], channels_users[channel_id]),
                )

                # Build the prompt for the agent
                prompt = json_dumps(
                    {
                        "user": (users[post_data["user_id"]]).username,
                        "message": message,
                    }
                )

                # Notify the channel that the bot is "typing"
                await self.send_typing(ws, channel_id, thread_id)

                # Run the agent with the constructed prompt and dependencies
                r = await self.infer(prompt, deps=deps, conversation_id=thread_id)

                # Send the agent's response as a reply in the current thread
                await self.client.post(
                    "/posts",
                    json={
                        "channel_id": channel_id,
                        "root_id": thread_id,
                        "message": r.output,
                    },
                )

    async def send_typing(
        self, ws: AsyncWebSocketSession, channel_id: str, thread_id: str
    ) -> None:
        self.ws_seq += 1
        await ws.send_json(
            {
                "action": "user_typing",
                "seq": self.ws_seq,
                "data": {
                    "channel_id": channel_id,
                    "parent_id": thread_id,
                },
            }
        )


def cmd_mattermost_register(parser: ArgumentParser) -> None:
    parser.set_defaults(func=cmd_mattermost)


async def cmd_mattermost(args: Namespace):
    async with MattermostAgent(
        base_url=environ["MATTERMOST_BASE_URL"], token=environ["MATTERMOST_TOKEN"]
    ) as client:
        await client.arun()
