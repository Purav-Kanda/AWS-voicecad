# Pitch and judge Q&A

Say only what is true and verified. Items marked **[you confirm]** are your own experience. Fill them in or delete them.

## 10-second version

"voicecad lets you ask a voice assistant for a 3D printable part. It asks for the missing measurements, refuses designs that will not print, and hands back an STL file."

## 30-second version

"Making a simple part, like a phone stand or a case for a Raspberry Pi, means opening CAD software and learning it. Voice assistants can talk, but they guess missing details. voicecad is an MCP server that asks for exactly the dimensions it needs, one question at a time, and checks the design against print limits before building it. The question logic is plain code, so it is tested. The language model only phrases the questions. The result is a real STL file that I printed."

## 2-minute talk

1. **Problem (20 s).** "Most people who own a 3D printer print other people's designs, because CAD is slow to learn. A voice assistant could close that gap, but a model that guesses dimensions gives you a part that does not fit."
2. **Idea (20 s).** "Keep the conversation state in code. A spec lists each field, its unit, limits and rules. A session decides what to ask next, skips questions that do not apply, converts spoken units, and re-checks the rules after every answer."
3. **Demo summary (30 s).** "I say 'I need a phone stand'. It asks the phone thickness and whether I want a cable hole. If I ask for a base that is too narrow, it explains and asks again. At the end it writes an STL and a preview image. There are five built-in parts: box, bracket, phone stand, laptop riser and electronics case. You can also upload your own STL file, say what it is, and resize it. It is scaled, not redesigned, and it warns you when uneven stretching would distort holes."
4. **How it is built (30 s).** "It is an MCP server over Streamable HTTP, protocol 2025-11-25, which is what the Alexa Plus track requires. The assistant in the demo is a Strands agent on Amazon Bedrock. The question engine is a separate open source library, guided-intake, under the MIT license."
5. **Honest limits and next step (20 s).** "I have not tested it on an Alexa Plus device. The checks are rules of thumb, not a slicer. Next I would add parametric parts from a user's own measurements and a slicer check."

## Judge Q&A

**Why not let the model ask the questions itself?**
Models forget fields, ask twice, or accept impossible values. Putting the state in code makes the behavior testable. There are 77 tests that run without any model. The model still handles the wording and understanding replies.

**Does it work on Alexa+?**
It is built to the Alexa+ track requirements: an MCP server over Streamable HTTP, protocol 2025-11-25 or later. I verified the protocol handshake. I have not run it on an Alexa+ device, because there is no local simulator, so the demo uses a browser page that simulates the assistant. I listed this as a feature request in the friction log.

**How do you know the parts will print?**
The server checks that parts fit the printer's bed, that walls are thick enough, that holes have material around them, and that the final mesh is watertight. It exports the bracket on its side so it needs no supports. I printed **[you confirm: which part, which printer, result]**. I do not claim every output prints.

**What is original here?**
The guided-intake library: conditional questions, rules that run only when their inputs exist, errors versus warnings, and hints for the assistant, all as plain code with no model dependency. voicecad is the first user of it.

**What was hard?**
Getting booleans right. My first gusset was inside out because of triangle winding, and the first stand design could not print without supports. Both are now covered by tests, for example a point-inside test proving the cable hole goes through the base.

**What would break first in production?**
No authentication on the endpoint, sessions held in memory, and one server process. All three are documented in the README.

**How does it use AWS?**
The demo assistant is a Strands Agents SDK agent calling Amazon Bedrock, and it reaches the tools through MCP. I used Claude Haiku 4.5 through a global cross-region inference profile in us-east-2. Setup took longer than the code, because of account quotas and the key type. The details are in the product feedback.

**Why open source the library separately?**
Slot filling shows up in many assistants: booking, ordering, forms. The library has no 3D printing code. Anyone can use it with any MCP server.

**Is the printer assumption fixed?**
No. The default is Ender 3 size. Set `VOICECAD_PRINTER` to a preset or a size such as `250x210x220`.

**Is the Raspberry Pi hole pattern right?**
It uses the commonly published 85 by 56 mm board with holes 58 by 49 mm apart, 3.5 mm from the edge. The assistant tells the user to check it against their own board. **[you confirm against your board if you have one]**

## What not to claim

- Tested on Alexa or Echo hardware.
- Prints successfully on every printer.
- Any number of users, speed or cost you did not measure.
