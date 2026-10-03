import sys

from pydantic_ai.messages import ModelMessagesTypeAdapter

with open(sys.argv[1], "rb") as file:
    data = ModelMessagesTypeAdapter.validate_json(file.read())

cost = 0
for run in data:
    try:
        cost += float(run.usage.cost)
    except AttributeError, ValueError:
        pass

print(cost)
