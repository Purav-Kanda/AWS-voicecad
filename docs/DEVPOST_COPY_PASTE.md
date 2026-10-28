# Devpost copy-paste pack

Paste each block into the matching Devpost field.

---

# 1. Project description and fields

# Devpost submission text

Copy each block into the matching field. Replace every `YOUR-...` and `[you confirm ...]` before submitting. Do not put your name or email in any of this unless a field asks for it.

## Project name

voicecad

## Elevator pitch (one line)

Ask your voice assistant for a 3D printable part. It asks for the missing measurements, checks the design, and returns an STL file.

## Tracks

- Alexa+ (main track).

## Mini challenges

- AWS Builder.
- Open Source (with the guided-intake library).

Reminder from the rules: one project can win one track prize and one mini challenge prize.

## Project description

### Inspiration

I bought my first 3D printer with my first co-op paycheques, and then hit a wall: the printer was the easy part. Learning CAD software, finding my way around a 3D workspace, and getting the dimensions right took far longer than the prints themselves. Most hobbyists do not want a second hobby in learning software. They just want a phone stand, a bracket or a hook that fits. So I built voicecad: tell your assistant what you want, answer a few simple questions, and get a file that is ready to print.

### What it does

voicecad is an MCP server that makes 3D printable parts by asking the user for dimensions. The assistant starts a conversation for a part such as a phone stand, asks one question at a time, accepts spoken units (millimeters, centimeters, meters, inches), and skips questions that have a sensible default. After every answer, the server re-checks the design against print rules: the part must fit the printer bed, walls must be thick enough, screw holes need material around them, and a laptop riser must tilt in a comfortable range. Designs that fail are explained in plain words and the assistant asks again. When the design is valid, the server builds the model, checks the real geometry is watertight, and writes STL files with a preview picture.

Five parts are available: storage box with lid, L bracket with gusset, phone stand with optional cable hole, laptop riser (two rails), and electronics case for a Raspberry Pi or a custom board with standoffs, vents and a port opening.

You can also bring your own model. Upload an STL file, say what it is, and choose how to size it: keep its size, set its longest side, scale by a percent, or set width, depth and height. The server scales the model and checks the result against the printer bed. It warns when uneven stretching would turn round holes oval, when a big shrink would thin the walls, and when the size looks like a different unit. It scales a model but does not redesign it, and it says so.

### How we built it

- **MCP server** in Python with the MCP SDK, over Streamable HTTP, speaking protocol version 2025-11-25.
- **guided-intake**, a separate open source library, holds the question flow and the rules as plain testable code. The language model never decides which question is next.
- **Geometry** with trimesh and manifold3d boolean operations. A small z-buffer renderer makes previews.
- **Assistant** in the demo is a Strands Agents SDK agent on Amazon Bedrock that connects to the server with MCPClient and calls its tools. A browser page simulates a voice assistant with the Web Speech API.
- **Structure:** each part is one module (questions, rules, geometry) listed in a registry, the printer is passed in as a profile, settings are read once at start up, and `server.py` is the only place that wires them together. See `docs/ARCHITECTURE.md`.

### Challenges

- Boolean geometry bugs: an inside-out gusset from wrong triangle winding, and a first phone stand design that needed supports. Both now have tests.
- Hard-coded assumptions: the first version assumed one printer bed and guessed a stand depth. Both were replaced by values computed or injected, with a test that pins the result.
- Making the protocol requirement visible: the SDK's default negotiated version is older than the track requires, so I wrote a handshake check script.

### Accomplishments

- Over 120 automated tests in voicecad (plus 13 in guided-intake). They include a seeded random sweep (every design the rules accept must build into a watertight mesh), an in-process test that drives the server through the real MCP protocol from first question to STL file and preview image, and a headless-browser test of the demo page. A larger one-off sweep of 596 random designs had no build failures.
- Lint and type checks pass in CI.
- I printed the phone stand it made on my own 3D printer, and it came out clean. I do not claim every output prints.

### What we learned

Do not trust the model to finish a job. Mine sometimes said a part was ready without calling the tool that builds it, so the server now tells the model the next step after every answer, and the agent checks that the file really exists. I also learned to keep all the rules and conversation state in code and let the model only talk, and to test the first live run against a real cloud account early, because quotas and keys took longer than the code.

### What's next

A slicer-based printability check, parts generated from the user's own measurements, authentication on the MCP endpoint, and a test on an Alexa+ device when a simulator or device access is available.

### Known limits (be honest, judges read this)

- Not tested on an Alexa+ device. The demo uses a simulated assistant in the browser.
- Printability checks are rules of thumb plus a watertight check, not a slicer.
- No authentication. Sessions are held in memory.

## Built with

Python, MCP Python SDK, Strands Agents SDK, Amazon Bedrock, trimesh, manifold3d, NumPy, Pillow, Starlette, uvicorn, Web Speech API.

## Try it out links

- Code: https://github.com/Purav-Kanda/AWS-voicecad
- Demo video: https://youtu.be/-sxyCuDjAyM

## Testing instructions (for judges)

```
git clone https://github.com/Purav-Kanda/guided-intake
git clone https://github.com/Purav-Kanda/AWS-voicecad
cd AWS-voicecad
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ../guided-intake -e ".[dev]"
pytest -q
```

The test suite needs no AWS account. It includes `tests/test_server_e2e.py`, which runs a whole conversation over the MCP protocol.

To run the server and check the protocol:

```
python -m voicecad.server &
python scripts/check_handshake.py
```

To run the voice demo, AWS credentials with Bedrock model access are needed (see README). Judges can skip this and watch the demo video.

## AWS Builder mini challenge

Which AWS tools or services did you use, and for what?

"Amazon Bedrock, through the Strands Agents SDK `BedrockModel`, powers the assistant that talks to the user. The Strands agent connects to the voicecad MCP server and calls its tools. I used Claude Haiku 4.5 through a global cross-region inference profile in us-east-2."

Product feedback: copy from `PRODUCT_FEEDBACK.md`.

## Friction log (up to 10 percent bonus)

Copy from `FRICTION_LOG.md`. Nine entries and two feature requests, all from this build.

## Open Source mini challenge

| Field | Value |
| --- | --- |
| Contribution URL | https://github.com/Purav-Kanda/guided-intake |
| Repository URL | https://github.com/Purav-Kanda/guided-intake |
| GitHub username | Purav-Kanda |

Description:

"guided-intake is an MIT-licensed Python library for slot filling in voice assistants and agents. You describe what you need to know as a spec (fields, units, limits, defaults, conditional fields, cross-field rules with error and warning levels, and hints for the assistant). A session then decides what to ask next, parses spoken numbers with units, and re-checks the rules after each answer. It ships MCP tools that plug into any MCP server. It has no model dependency, so the question flow is unit tested. voicecad is its first user."

## Submission checklist (mapped to the rules)

- [ ] Both repositories are public and show an open source license (MIT) at the top.
- [ ] README explains what it is and how to run it.
- [ ] Demo video: under 3 minutes, public on YouTube or Vimeo, English, no copyrighted music, no third-party trademarks.
- [ ] Description covers features and functionality.
- [ ] Testing instructions given.
- [ ] Alexa+ track: MCP server over Streamable HTTP, protocol 2025-11-25 or later (run `scripts/check_handshake.py` and keep the output).
- [ ] AWS Builder: Bedrock use described, product feedback filled in with your own experience.
- [ ] Open Source: contribution URL, repository URL, GitHub username and description entered.
- [ ] Friction log pasted.
- [ ] All `YOUR-...` and `[you confirm ...]` text removed.
- [ ] Submitted before the deadline, Friday October 23, 2026 at 3:00 pm Eastern. Aim for at least a day earlier.

---

# 2. AWS Builder product feedback

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

---

# 3. Friction log

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

## 7. A new Bedrock account had reduced quotas, and the error blamed daily token use

- **Task:** Run the demo assistant on Amazon Bedrock for the first time.
- **Steps:** Called Claude models through Strands `BedrockModel` in us-east-2, then tried several newer Claude models to see which one worked.
- **Expected:** The models listed in the console work.
- **Actual:** Anthropic models first needed a use case form. After that, only Claude Haiku 4.5 and Nova 2 Lite worked. The newer Claude models returned access or quota errors, and one message said "too many tokens per day", which made it look like I had used too much when the account just had reduced quotas.
- **Severity:** High. It cost the most time of anything in this build.
- **Workaround:** Wrote `scripts/check_bedrock.py`, which tries a list of model IDs and shows which ones work, then used Haiku 4.5 through a global cross-region inference profile.
- **Suggestion:** Say in the error when the cause is a reduced account quota or a missing use case form, and link to where to fix it. Show on the model page which models a new account can call.

## 8. Short-term and long-term Bedrock API keys give the same "Invalid API Key format" error

- **Task:** Give a script credentials for Bedrock.
- **Steps:** Set `AWS_BEARER_TOKEN_BEDROCK` to a short-term key, which had expired, then to a value that was not a key.
- **Expected:** An error that says the key expired or is the wrong type.
- **Actual:** "Invalid API Key format" for both cases. The long-term key that worked starts with `ABSK`. In a new PowerShell window the variable was not set at all, which gave "Unable to locate credentials".
- **Severity:** Medium.
- **Workaround:** Generated a long-term key with a one day expiry, checked its prefix without printing it, and set the variable in the same window that runs the app.
- **Suggestion:** Say whether a key has expired or is the wrong kind, and show the key type in the console next to each key.

## 9. A temporary Bedrock error that went away on retry

- **Task:** Run the live assistant.
- **Steps:** Sent a normal request once.
- **Expected:** A response.
- **Actual:** One `ServiceUnavailableException`, and the same request worked on the next try.
- **Severity:** Low.
- **Workaround:** The demo page shows AWS's own error text so the cause is visible, and a retry fixed it.
- **Suggestion:** Say in the error whether a retry is expected to work.

## Feature requests

- **A local test harness for Alexa+ MCP servers (Important).** There was no way to try the server against Alexa+ itself, so the demo uses a simulated assistant. A downloadable simulator that calls MCP tools the way Alexa+ does would let developers test before submitting.
- **A Windows build of Kiro Crew (Nice-to-have).** Kiro Crew qualifies for the AWS Builder challenge on its own, but launch coverage describes a macOS app. I did not try to install it, so this is from reading, not from an attempt.
