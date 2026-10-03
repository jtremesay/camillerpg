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

import asyncio
from argparse import ArgumentParser
from collections.abc import Iterable

from dotenv import load_dotenv

try:
    import logfire
except ImportError:
    logfire = None

from .mattermost import cmd_mattermost_register

_COMMANDS = {
    "mattermost": cmd_mattermost_register,
}


def main(args: Iterable[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("-e", "--env-file", help="Path to the environment file")

    # Set up the argument parser and sub-commands
    sub_parsers = parser.add_subparsers(dest="command")
    for command, register_func in _COMMANDS.items():
        register_func(sub_parsers.add_parser(command))

    # Parse the command-line arguments
    parsed_args = parser.parse_args(args)

    # Load environment variables from the specified file
    load_dotenv(parsed_args.env_file)

    if logfire is not None:
        logfire.configure(send_to_logfire="if-token-present")
        logfire.instrument_httpx()
        logfire.instrument_pydantic_ai()

    # Execute the appropriate command function if specified
    if func := getattr(parsed_args, "func", None):
        asyncio.run(func(parsed_args))
    else:
        parser.print_help()
