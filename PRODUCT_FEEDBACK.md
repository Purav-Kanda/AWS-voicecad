# Product feedback (draft for the Devpost form)

Sections marked **TODO** need your own experience from a live run. Fill them in after you have run the demo against Bedrock. Do not submit this file with the TODO lines still in it.

## Which tools, APIs and SDKs were used, and for what

- **MCP Python SDK 2.1.1** (`mcp`): the voicecad server, over Streamable HTTP, speaking protocol 2025-11-25.
- **Strands Agents SDK 1.61.1**: the assistant agent. It connects to the MCP server with `MCPClient(url=...)` and calls the tools.
- **Amazon Bedrock** (through Strands `BedrockModel`): the language model behind the assistant. **TODO:** add the model ID and region you actually used.

AWS Builder: Strands Agents SDK on Amazon Bedrock, with the agent calling MCP tools. **TODO:** confirm after your first live run, and add anything else you used.

## What worked well

- Creating an MCP server took very little code: a decorator per tool and one `run("streamable-http")` call.
- `MCPClient(url=...)` in Strands connected to the server over HTTP on the first try and listed all of the intake tools.
- The MCP SDK's DNS rebinding protection blocks the default test host name with only a log line. See entry 6.
- The MCP SDK's import error named the migration guide, which saved time.
- **TODO:** Bedrock setup, docs and reliability, from your own run.

## What needs work

- Strands pins `mcp` below 2.2, so installing it downgrades the MCP SDK. See friction log entry 3.
- The MCP SDK's default negotiated protocol version (2025-03-26) is older than the version the Alexa+ track requires (2025-11-25), and nothing makes that obvious. See entry 4.
- No way to test against Alexa+ itself, so the demo uses a simulated assistant.
- **TODO:** anything that went wrong with Bedrock, such as model access, region or inference profile names.

## Onboarding experience (zero to hello world)

- MCP server: about a few minutes to a working tool list once the 2.x class name was known.
- **TODO:** time and steps to a first Bedrock response.

## Would you build with these again?

**TODO:** answer Yes or No, with your honest reason.
