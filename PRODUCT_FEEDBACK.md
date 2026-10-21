# Product feedback (draft for the Devpost form)

## Which tools, APIs and SDKs were used, and for what

- **MCP Python SDK 2.1.1** (`mcp`): the voicecad server, over Streamable HTTP, speaking protocol 2025-11-25.
- **Strands Agents SDK 1.61.1**: the assistant agent. It connects to the MCP server with `MCPClient(url=...)` and calls the tools.
- **Amazon Bedrock** (through Strands `BedrockModel`): the language model behind the assistant. I used Claude Haiku 4.5 through a `global.` cross-region inference profile, in us-east-2, with a long-term Bedrock API key (`AWS_BEARER_TOKEN_BEDROCK`).

AWS Builder: Strands Agents SDK on Amazon Bedrock, with the agent calling MCP tools. I ran it live and it asks the questions, calls `finish` and produces the STL file.

## What worked well

- Creating an MCP server took very little code: a decorator per tool and one `run("streamable-http")` call.
- `MCPClient(url=...)` in Strands connected to the server over HTTP on the first try and listed all of the intake tools.
- The MCP SDK's DNS rebinding protection blocks the default test host name with only a log line. See entry 6.
- The MCP SDK's import error named the migration guide, which saved time.
- Once a key worked, Strands plus Bedrock needed no custom glue: `BedrockModel`, `MCPClient` and `Agent` were enough for a working tool-calling loop.
- Haiku 4.5 follows tool instructions well. With clear rules it asks one question at a time and reads rule errors back in plain words.
- Long-term Bedrock API keys are a simple way to get credentials into a script, once the key is the right kind (see below).

## What needs work

- Strands pins `mcp` below 2.2, so installing it downgrades the MCP SDK. See friction log entry 3.
- The MCP SDK's default negotiated protocol version (2025-03-26) is older than the version the Alexa+ track requires (2025-11-25), and nothing makes that obvious. See entry 4.
- No way to test against Alexa+ itself, so the demo uses a simulated assistant.
- **Account quotas.** A new account had reduced quotas. Haiku 4.5 and Nova 2 Lite worked, but the newer Claude models I tried returned access or quota errors. The message said "too many tokens per day", which made it look like a usage problem when the real cause was the reduced account limit.
- **Use case form.** Anthropic models needed a use case form first. The error did not say that clearly, and I only found it after reading the full AWS error text. A direct link to the form in the error would save time.
- **Two kinds of keys.** Short-term Bedrock API keys expire, and the error I got ("Invalid API Key format") did not say it was expired. Long-term keys start with `ABSK`. A key ID pasted by mistake gives the same error. A clearer message for each case would help.
- **Temporary errors.** I got one `ServiceUnavailableException` that went away on retry. The app now shows AWS's own words so the cause is visible.
- **Model IDs.** Which model ID or inference profile to use in which region was hard to find. I wrote `scripts/check_bedrock.py` to try several IDs and show which ones work.
- **Credentials on Windows.** Setting `AWS_BEARER_TOKEN_BEDROCK` in one PowerShell window does not carry over to a new window, which gave "Unable to locate credentials".

## Problems we hit while building, and how we fixed them

These are about my own app, not the platform. They are in the friction log with more detail.

- **The assistant said a part was ready, but no file existed.** The model sometimes skipped the `finish` tool and replied as if it had finished. Fix: the server now returns a `next_step` hint after every answer, the agent checks that `finish` succeeded and nudges the model once if it did not, and the instructions say never to call a part ready before `finish` returns files.
- **The assistant invented real product sizes.** For an AirPods case it stated made-up dimensions as fact. Fix: an instruction to never state the size of a real product as fact and to ask the user instead.
- **Uploaded models with holes.** Fixing holes in an uploaded STL needs `networkx`, which trimesh does not install by default. A test failed on my machine because of it. Fix: declared the dependency, and a failed repair now returns a plain message instead of a crash.
- **Windows test failure.** A test used a huge value as a pytest parameter, and Windows rejects environment variables over 32,767 characters. Fix: build the data inside the test.
- **CI failures from newer libraries.** CI installed newer Pillow and trimesh than my machine and mypy failed. Fix: use `Image.Resampling.LANCZOS` and `trimesh.load_mesh`.
- **Second repository.** The question engine lives in its own library, so CI had to install it from GitHub. It failed until that repo was public.

## Onboarding experience (zero to hello world)

- MCP server: about a few minutes to a working tool list once the 2.x class name was known.
- Bedrock: the first response took much longer than the MCP side because of the use case form, the quota limits and the key type. After that, a response took a few minutes of work. A short "first call" guide that shows the right key type and a model that works on a new account would cut this a lot.

## Would you build with these again?

**Yes.** MCP and Strands are small and quick to start with, and Bedrock gives a managed model without running anything myself. What would stop me is the setup time for a new account. I would use them again for any tool-calling assistant, and I would check quotas and keys first.
