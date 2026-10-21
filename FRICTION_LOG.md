# Friction log

Problems hit while building voicecad for the Alexa+ track and the AWS Builder mini challenge. Each entry is something that actually happened during this build.

## 1. Hackathon AWS credits ran out, but the AWS Builder instructions still assume them

- **Task:** Plan the AWS Builder entry (Bedrock plus the Strands SDK).
- **Steps:** Read the Rules page, which describes requesting $150 in AWS credits, then the Resources page, which says the credit codes ran out on October 7.
- **Expected:** A clear path to use Bedrock for the challenge.
- **Actual:** The Rules page still describes the credit request, with a short update note added. Someone joining after the codes ran out may have to pay for Bedrock calls themselves. The Resources page says the free tier is "enough to get started" but does not say whether Bedrock model calls are covered by it.
- **Severity:** Medium.
- **Workaround:** Built every part that does not need AWS first (intake engine, geometry, MCP server) so the AWS piece stays small.
- **Suggestion:** State on both pages which AWS services are covered by the free tier, and mark the credits section as closed.

## 2. MCP Python SDK 2.x renamed the server class, so most tutorials fail

- **Task:** Create the MCP server for the Alexa+ track.
- **Steps:** `pip install mcp` and imported `FastMCP` from `mcp.server.fastmcp`, as most existing guides show.
- **Expected:** The import works.
- **Actual:** `ModuleNotFoundError`. In 2.x the class is `MCPServer` in `mcp.server.mcpserver`. The error text linked to the migration guide, which helped.
- **Severity:** Low.
- **Workaround:** Followed the migration note and read the constructor and `run` signatures directly.
- **Suggestion:** The hackathon resources should say which major version of the MCP SDK the examples use.

## 3. Strands Agents pins an older MCP SDK than the one pip installs by default

- **Task:** Add the Strands Agents SDK to a project that already used the latest MCP SDK.
- **Steps:** `pip install strands-agents` in an environment with `mcp` 2.2.0.
- **Expected:** Both work together.
- **Actual:** Strands requires `mcp` below 2.2, so pip downgraded `mcp` to 2.1.1. Everything still worked, but the server had been developed against 2.2.0.
- **Severity:** Low.
- **Workaround:** Pinned `mcp>=2.0,<2.2` in the project and re-ran the tests and the protocol check after the downgrade.
- **Suggestion:** Widen the pin, or document the compatible MCP SDK range.

## 4. The SDK's default protocol version is older than the version the track requires

- **Task:** Be sure the server meets the Alexa+ requirement of MCP spec 2025-11-25 or later over Streamable HTTP.
- **Steps:** Checked the SDK's version constants.
- **Expected:** An obvious sign that the server meets the requirement.
- **Actual:** The SDK reports a latest version of 2026-07-28 but a default negotiated version of 2025-03-26. Nothing says which one a given client will get.
- **Severity:** Medium for newcomers, since the requirement is easy to miss.
- **Workaround:** Wrote `scripts/check_handshake.py`, which sends an initialize request asking for 2025-11-25 and prints what the server agrees to.
- **Suggestion:** Publish a small conformance check for Alexa+ MCP servers, or a checklist of what the track's judges verify.

## 5. The submission instructions name a reviewer who is not in the official list

- **Task:** Work out whom to add as a collaborator on a private repository.
- **Steps:** Compared the "Amazon Developer Relations GitHub profiles" list with the sentence below it.
- **Expected:** One consistent list.
- **Actual:** The list names five accounts. The sentence under it adds a sixth account that is not in the list.
- **Severity:** Low.
- **Workaround:** Use a public repository with an open-source license, which needs no collaborators.
- **Suggestion:** Use a single list in one place.

## 6. The MCP server rejects the standard test host name with only a log line to explain it

- **Task:** Test the server in process with Starlette's `TestClient`.
- **Steps:** Called `/mcp` through `TestClient(app)` with its default base URL.
- **Expected:** A normal response.
- **Actual:** Every request failed. The only explanation was a server log warning, `Invalid Host header: testserver`, from the SDK's DNS rebinding protection. The response itself had no content type, so the test crashed on a missing header instead of showing the cause.
- **Severity:** Low.
- **Workaround:** Created the client with `base_url="http://127.0.0.1:8000"`, which the protection allows.
- **Suggestion:** Return a readable error body for a rejected host, and mention the allowed hosts in the testing docs.

## Feature requests

- **A local test harness for Alexa+ MCP servers (Important).** There was no way to try the server against Alexa+ itself, so the demo uses a simulated assistant. A downloadable simulator that calls MCP tools the way Alexa+ does would let developers test before submitting.
- **A Windows build of Kiro Crew (Nice-to-have).** Kiro Crew qualifies for the AWS Builder challenge on its own, but launch coverage describes a macOS app. I did not try to install it, so this is from reading, not from an attempt.
