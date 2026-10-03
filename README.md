# CamilleRPG

A game master bot for animating your tabletop RPG sessions.

## Installation

```shell
$ git clone https://github.com/jtremesay/camillerpg.git
$ cd camillerpg
$ uv sync
```

## Optional Dependencies

- `mattermost`: mattermost integration
- `anthropic`: Anthropic API integration
- `bedrock`: AWS Bedrock integration
- `google`: Google Generative Language API integration
- `ollama`: Ollama API integration
- `logfire`: Logfire logging integration

Install optional dependencies as needed:

```shell
$ uv sync --extra <deps1,deps2,...>
```

Example for installing Mattermost and Ollama optional dependencies:

```shell
$ uv sync --extra mattermost,ollama
```

## Configuration

CamilleRPG is configured through environment variables. You can use a `.env` file to set them conveniently. (or `camillerpg -e <.env file>` command).

- `CAMILLE_MODEL` - The model to use for CamilleRPG. See here for available models: https://pydantic.dev/docs/ai/models/overview/. Required
- `CAMILLE_MODEL_COMPACTION` - The model used for compacting the history of long conversations. Use $CAMILLE_MODEL if not specified.
- `MATTERMOST_BASE_URL` - The base URL of your Mattermost instance. Required if using Mattermost integration.
- `MATTERMOST_TOKEN` - The API key for your Mattermost instance. Required if using Mattermost integration.
- `ANTHROPIC_API_KEY` - The API key for using Anthropic's API. Required if using Anthropic integration.
- `AWS_BEARER_TOKEN_BEDROCK` - The bearer token for using AWS Bedrock. Required if using AWS Bedrock integration.
- `AWS_DEFAULT_REGION` - The default AWS region to use for AWS Bedrock. Required if using AWS Bedrock integration.
- `AWS_ACCESS_KEY_ID` - The access key ID for using AWS Bedrock. Alternative to using `AWS_BEARER_TOKEN_BEDROCK`
- `AWS_SECRET_ACCESS_KEY` - The secret access key for using AWS Bedrock. Alternative to using `AWS_BEARER_TOKEN_BEDROCK`
- `GOOGLE_API_KEY` - The API key for using the Google Generative Language API. Required if using Google GLA integration.
- `OLLAMA_BASE_URL` - The base URL for using Ollama's API. Required if using Ollama integration.
- `OLLAMA_API_KEY` - The API key for using Ollama's API. Optional.
- `LOGFIRE_TOKEN` - The API key for enabling Logfire logging. Optional

## Usage

### Mattermost

```shell
$ uv run camillerpg mattermost
```