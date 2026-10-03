# CamilleRPG

A game master bot for animating your tabletop RPG sessions.

## Installation

```shell
$ git clone https://github.com/jtremesay/camillerpg.git
$ cd camillerpg
$ uv sync
```

## Optional Dependencies

### Mattermost

For using CamilleRPG with Mattermost:

```shell
$ uv sync --extra mattermost
```

### Logfire

For enabling the logging with Logfire:

```shell
$ uv sync --extra logfire
```

### GoogleGLA

For inferring with Google Generative Language API:

```shell
$ uv sync --extra google
```

## Configuration

CamilleRPG is configured through environment variables. You can use a `.env` file to set them conveniently. (or `camillerpg -e <.env file>` command).

- `MATTERMOST_BASE_URL` - The base URL of your Mattermost instance. Required if using Mattermost integration.
- `MATTERMOST_TOKEN` - The API key for your Mattermost instance. Required if using Mattermost integration.
- `GOOGLE_API_KEY` - The API key for using the Google Generative Language API. Required if using Google GLA integration.
- `LOGFIRE_TOKEN` - The API key for enabling Logfire logging. Required if using Logfire integration.

## Usage

### Mattermost

```shell
$ uv run camillerpg mattermost
```