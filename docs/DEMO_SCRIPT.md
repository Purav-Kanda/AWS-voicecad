# Demo video script (target 2:35, hard limit 3:00)

Rules to respect: under 3 minutes, public on YouTube or Vimeo, English, no copyrighted music, no third-party logos. Judges may stop watching at 3:00, so the finished printed part must appear before 2:00.

Speaking pace is about 150 words per minute. The narration below is about 175 words, roughly 70 seconds. The rest of the time is the live conversation and the screen shots, so do not fill every second with talking.

**Before you record**
- [ ] Server and demo page running, AWS credentials set, one dry run done end to end.
- [ ] One part already printed (the phone stand takes the least time). Put it on the desk, next to the laptop.
- [ ] Browser zoom 125 percent, notifications off, no personal tabs open.
- [ ] Terminal ready with `python scripts/check_handshake.py` typed but not run.
- [ ] Mic test. Record the voice and screen together at 1080p.

Your actual wording will differ because the assistant's replies vary. Do not read the assistant lines. Say what you see.

## Shot list

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00 to 0:15 | You, then the printed phone stand in hand | "I wanted a phone stand. Designing one in CAD takes an hour. So I asked my voice assistant. This is voicecad." |
| 0:15 to 0:35 | Demo page. Press Mic. | "voicecad is an MCP server for Alexa Plus. It makes 3D printable parts, but it will not guess your measurements. It asks." |
| 0:35 to 1:15 | The conversation. Say: "I need a phone stand." Answer 11 millimeters. Say yes to the cable hole. | "Watch what it asks. Only the phone thickness and the cable hole. Angle and width have defaults. If I give two answers in one sentence, it takes both." |
| 1:15 to 1:40 | Say: "Make the base 30 millimeters wide." Show the rejection. | "Now I make a mistake. Too narrow to hold a phone. The assistant tells me why and asks again. That check is code, not the model's opinion." |
| 1:40 to 2:00 | Correct it. Finish. Show the preview and the three numbers. Cut to the printed part. | "Here is the model, and here it is printed. Same part." |
| 2:00 to 2:20 | Terminal: run the handshake script and the test command. Show "agreed to protocol: 2025-11-25" and the passing count. | "The server speaks MCP protocol 2025-11-25 over Streamable HTTP, the version the Alexa Plus track needs. 77 tests cover the questions, the rules and the geometry." |
| 2:20 to 2:35 | Browser: guided-intake repo page, then the architecture diagram | "The question engine is a separate open source library, guided-intake. Any MCP server can use it. Thanks for watching." |

## Narration, full text (read at a calm pace)

> I wanted a phone stand. Designing one in CAD takes an hour. So I asked my voice assistant. This is voicecad.
>
> voicecad is an MCP server for Alexa Plus. It makes 3D printable parts, but it will not guess your measurements. It asks.
>
> Watch what it asks. Only the phone thickness and the cable hole. The angle and the width have sensible defaults. If I give two answers in one sentence, it takes both.
>
> Now I make a mistake: a base that is too narrow to hold a phone. The assistant tells me why, and asks again. That check is code, not the model's opinion.
>
> Here is the model, and here it is printed. Same part.
>
> The server speaks MCP protocol 2025-11-25 over Streamable HTTP, the version the Alexa Plus track needs. Seventy-seven tests cover the questions, the rules and the geometry.
>
> The question engine is a separate open source library, guided-intake, so any MCP server can use it. The assistant runs on Amazon Bedrock with the Strands Agents SDK. Thanks for watching.

## Fallback if the live demo misbehaves

Models give different wording every run. If a take goes wrong, do not fix it live.
1. Record the take anyway and use the best one. Cut dead time.
2. If Bedrock is unreachable, start the page with `VOICECAD_OFFLINE=1`. It uses a plain keyword script instead of a language model, but the questions, rules and files are the real ones. Say plainly: "This is the offline mode, not the language model." Do not imply Alexa is running. You can also run `python scripts/check_handshake.py` and show `tests/test_server_e2e.py` passing.
3. Never show a part that was not made by the app in the video. If the print failed, show the model preview and say the print is not shown.

## Do not say

- "Works on Alexa" or "tested on an Echo". It has not been tested on an Alexa+ device.
- "Guaranteed to print". Say "checked against common printer limits".
- Any claim about speed or cost that you did not measure.

## YouTube description (paste)

```
voicecad: a voice-guided 3D part maker for Alexa+.
An MCP server (Streamable HTTP, protocol 2025-11-25) that asks for missing dimensions,
checks printability, and returns STL files.

Code: https://github.com/Purav-Kanda/AWS-voicecad
Open source library: https://github.com/Purav-Kanda/guided-intake

Built with: MCP Python SDK, Strands Agents SDK, Amazon Bedrock, trimesh, manifold3d.
Made for the Amazon Developer Hackathon.
```

## Upload checklist

- [ ] Length under 3:00 (check the final file, not the timeline).
- [ ] Visibility set to Public (not Unlisted, not Private).
- [ ] Spoken and captioned in English. Add captions in YouTube Studio.
- [ ] No copyrighted music. No third-party logos on screen.
- [ ] Open the link in a private window and watch the first 10 seconds.
