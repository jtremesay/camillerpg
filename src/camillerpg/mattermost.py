from typing import cast

from httpx2 import AsyncClient


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
