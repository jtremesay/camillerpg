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
from dataclasses import asdict, dataclass
from json import dumps as json_dumps
from os import environ

from pydantic_ai import Agent, AgentRunResult, RunContext
from pydantic_ai_harness import StepPersistence, SummarizingCompaction
from pydantic_ai_harness.step_persistence import FileStepStore, continue_run


@dataclass
class User:
    pass


@dataclass
class Deps:
    me_name: str
    users: list[User]


class CamilleAgent:
    def __init__(self) -> None:
        model_name = environ["CAMILLE_MODEL"]
        compaction_model_name = environ.get("CAMILLE_MODEL_COMPACTION")
        self.store = FileStepStore(".history")

        self.agent = Agent(
            model=model_name,
            deps_type=Deps,
            capabilities=[
                StepPersistence(store=self.store),
                SummarizingCompaction(model=compaction_model_name, max_fraction=0.9),
            ],
        )
        self.agent.system_prompt(dynamic=True)(self.system_prompt)

    def system_prompt(self, ctx: RunContext[Deps]) -> str:
        deps = ctx.deps

        p = f"""\
Tu es {deps.me_name}, le maitre du jeu sur un groupe de discussion.

On joue de manière narrative, sans réels règles strictes. Garde l'histoire cohérente et immersive. 
Laisse le temps aux joueurs de réagir et d'interagir avant de faire avancer l'histoire. 
Empêche les de faire des actions incohérentes ou qui casseraient l'immersion.

Les joueurs sont :
```jsonl
"""

        for user_data in deps.users:
            p += f"{json_dumps(asdict(user_data))}\n"
        p += "```"

        return p

    async def infer(
        self, prompt: str, deps: Deps, conversation_id: str
    ) -> AgentRunResult[str]:
        try:
            prior_run = (await self.store.list_runs(conversation_id=conversation_id))[
                -1
            ].run_id
        except IndexError:
            history = None
        else:
            history = await continue_run(self.store, run_id=prior_run)

        return await self.agent.run(
            prompt,
            deps=deps,
            conversation_id=conversation_id,
            message_history=history,
        )
