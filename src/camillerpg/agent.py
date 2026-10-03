from dataclasses import dataclass
from json import dumps as json_dumps

from aiofiles import open as aopen
from aiofiles.os import replace as areplace
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelRequest, ModelResponse
from pydantic_ai_harness import SummarizingCompaction


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

On joue de manière narrative, sans réels règles strictes. 

Les joueurs sont :
```jsonl
"""

    for user_data in users:
        p += f"{json_dumps(user_data)}\n"
    p += "```"

    return p


def get_agent() -> Agent[Deps]:
    agent = Agent(
        model="google:gemini-3.5-flash-lite",
        deps_type=Deps,
        capabilities=[
            SummarizingCompaction(
                model="google:gemini-3.5-flash-lite", max_fraction=0.5
            )
        ],
    )
    agent.system_prompt()(system_prompt)

    return agent


def get_history_name(channel_id: str, thread_id: str) -> str:
    return f"history_{channel_id}_{thread_id}.json"


async def read_history(
    channel_id: str, thread_id: str
) -> list[ModelRequest | ModelResponse]:
    history_name = get_history_name(channel_id, thread_id)
    try:
        async with aopen(history_name, "rb") as f:
            data = await f.read()
    except FileNotFoundError:
        return []

    return ModelMessagesTypeAdapter.validate_json(data)


async def write_history(
    channel_id: str, thread_id: str, history: list[ModelRequest | ModelResponse]
) -> None:
    data = ModelMessagesTypeAdapter.dump_json(history, indent=2)

    history_name = get_history_name(channel_id, thread_id)
    tmp_history_name = f"{history_name}.tmp"
    async with aopen(tmp_history_name, "wb") as f:
        await f.write(data)

    await areplace(tmp_history_name, history_name)
