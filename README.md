# voicecad

Talk to an assistant, answer a few questions, and get a 3D-printable STL file.

voicecad is an MCP server (Streamable HTTP) that makes simple printable parts. The assistant asks only for the dimensions that are missing, converts spoken units, checks the design against basic print rules, and returns real STL files. A small web page acts as a simulated voice assistant so you can try the whole flow.

Parts it can make today: a **storage box** (with optional lid), an **L bracket** (screw holes, optional gusset), a **phone stand** (optional charging cable hole), a **laptop riser**, an **electronics case**, and **your own model**: upload an STL, say what it is, and resize it to fit.

## How it works

```
person  ->  voice assistant page  ->  Strands agent on Amazon Bedrock
                                          |  MCP over Streamable HTTP
                                          v
                                  voicecad MCP server
                       guided-intake (questions + rules)  ->  trimesh/manifold builders  ->  STL
```

- The **conversation logic is code, not prompt**. `guided-intake` (a separate open-source library) tracks which answers are in, picks the next question and runs the rules. The model only talks to the person and passes answers along.
- **Rules run twice.** Design rules run during the conversation, so a problem is caught as soon as the needed answers exist. Then the real geometry is checked after it is built: the model must be watertight and fit the print bed.
- **Parts are built directly as meshes** with `trimesh` and `manifold3d`. No CAD program has to be installed.

## Requirements

- Python 3.11 or newer (tested on 3.11, 3.12 and 3.13)
- For the voice-assistant demo only: an AWS account with Amazon Bedrock model access in your region, and AWS credentials. The MCP server and the part builders do not need AWS.

## Setup

Clone `guided-intake` next to this repo, then:

```
pip install -e ../guided-intake
pip install -e ".[dev]"
```

Run the tests:

```
pytest
```

## Run the MCP server only

macOS or Linux:

```
VOICECAD_OUT=out python -m voicecad.server
```

Windows PowerShell:

```
$env:VOICECAD_OUT="out"; python -m voicecad.server
```

It listens on `http://127.0.0.1:8000/mcp` (change with `VOICECAD_HOST` and `VOICECAD_PORT`). Any MCP client can connect.

Check that the server speaks MCP protocol 2025-11-25 and runs the first step of an intake:

```
python scripts/check_handshake.py
```

## Run the voice assistant demo

Set up AWS credentials the usual way (`aws configure`, or the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_REGION` environment variables), and make sure Bedrock model access is enabled for your account and region. Then:

```
python -m uvicorn voicecad.web:create_demo_app --factory --port 8000
```

Open `http://127.0.0.1:8000`. Type, or press Mic (Chrome or Edge) to speak. Replies are spoken aloud if "Speak replies" is on. When a part is finished you get a preview image and a download link for each STL.

### No AWS account? Use offline mode

```
VOICECAD_OFFLINE=1 python -m uvicorn voicecad.web:create_demo_app --factory --port 8000
```

This swaps the language model for a plain keyword script. It is not an AI assistant: it picks the part from a keyword and treats each reply as the answer to the last question. The questions, rules, geometry and files are the same code as the real server. If a rule rejects an answer, it explains why and asks the size questions again.

The Bedrock model defaults to the Strands library default. To pick another, set `VOICECAD_MODEL_ID` to a model or inference profile ID you have access to.

## What it asks

| Part | Asked every time | Has a default (can be changed) |
| --- | --- | --- |
| Storage box | width, depth, height, lid (and snug or loose if a lid) | wall 2 mm |
| L bracket | flat arm, upright arm, width | thickness 4 mm, hole 4 mm, gusset yes |
| Phone stand | phone thickness, cable hole | angle 65 degrees, base width 85 mm |
| Laptop riser | rail length, rear height | front height 15 mm, rail width 30 mm, openings yes. Print the rail twice |
| Electronics case | board (Raspberry Pi or custom), vents, port side (plus five measurements if custom) | component height 17 mm, standoff 5 mm, screw hole 2.7 mm, gap 1 mm, wall 2 mm |
| Resized model (your STL) | the upload, what it is, and how to size it: keep, longest side, percent, or width, depth and height | none |

Numbers can be spoken in millimeters, centimeters, meters or inches.

### Your own model

Press **Upload** on the demo page and pick an `.stl` file (up to 10 MB). The page tells the assistant the file's id, and the assistant asks what it is and how big you want it. The model is scaled, never edited, so its shape stays as it was. Be aware of three limits:
- Stretching one side more than another turns round holes oval and changes wall thickness. You get a warning.
- STL files carry no units. Sizes are read as millimeters, and you get a warning if the size looks like another unit.
- The model must be a closed solid. Small holes in the surface are repaired. If it still has holes, the upload is refused with a reason.

MCP clients can use the same part: put the file in the uploads folder and pass its id as `upload_id`. Uploads are deleted after `VOICECAD_RETENTION_HOURS`.

The Raspberry Pi preset uses an 85 by 56 mm board with mounting holes 58 by 49 mm apart. Measure your own board before printing, because boards and revisions differ.

## Print rules it applies

- Parts must fit the printer's bed. The default is 220 by 220 by 250 mm (Ender 3 size). Pick another with `VOICECAD_PRINTER`: a preset name (`ender3`, `prusa_mk4`, `bambu_256`, `small_180`) or `WIDTHxDEPTHxHEIGHT`. A part may be turned a quarter turn to fit.
- Walls under 1.2 mm trigger a warning. Walls that leave less than 10 mm inside a box are an error.
- A bracket hole needs 3 mm of material at each edge, and each arm must be long enough for a hole.
- The gusset is skipped, with a note, if it would cover a screw hole.
- The laptop riser needs the rear at least 5 mm above the front, and warns above a 15 degree tilt.
- Case mounting holes must lie on the board.
- The bracket is exported lying on its side, and the phone stand leans back by at most 40 degrees from vertical, so neither needs supports.
- A finished model must be watertight, or it is refused.

## Settings

All optional, read once at start up.

| Variable | Default | Meaning |
| --- | --- | --- |
| `VOICECAD_OUT` | `out` | Folder for STL and preview files |
| `VOICECAD_HOST`, `VOICECAD_PORT` | `127.0.0.1`, `8000` | Where the server listens |
| `VOICECAD_PRINTER` | `ender3` | Bed size, see above |
| `VOICECAD_RETENTION_HOURS` | `24` | Files older than this are deleted when a new part is finished or a model is uploaded |
| `VOICECAD_MAX_UPLOAD_MB` | `10` | Largest STL the upload button accepts |
| `VOICECAD_MODEL_ID` | library default | Bedrock model for the demo agent |

## Tools the server exposes

`list_specs`, `start_intake`, `submit_answers`, `review` and `finish` come from `guided-intake`. `preview_part(file)` is added here and returns a picture of a finished part.

## Layout

- `parts/`: one module per part, holding its questions, its rules and its geometry. `parts/registry.py` lists them.
- `catalog.py`: builds each part's questions for the chosen printer and runs builds.
- `printer.py`, `config.py`: printer profile and settings.
- `geometry.py`, `checks.py`, `files.py`: shared geometry helpers, shared print rules, safe file handling.
- `build.py`: builds the part, checks the real mesh, writes STL files.
- `server.py`: the only place that wires everything together.
- `agent.py`: the Strands agent on Bedrock. `offline.py`: the no-model stand-in. `web.py` and `static/index.html`: the demo page.
- `scripts/check_handshake.py`: protocol check.
- `docs/`: architecture notes, demo script, pitch, Devpost text.

To add a part, see `docs/ARCHITECTURE.md`.

## Develop

```
pip install -e ".[dev]" ruff mypy
ruff check . && mypy && pytest -q
```

The browser test (`tests/test_ui.py`) needs Playwright and a Chromium install. It is skipped if they are missing.

`python scripts/render_gallery.py` renders one example of each part into `docs/images`.

## Hackathon entry notes

- **Track:** Alexa+. This is a self-hosted MCP server using Streamable HTTP. The demo page is a simulated assistant. The server has not been tested on an Alexa+ device.
- **AWS Builder:** the assistant is a Strands Agents SDK agent that calls Amazon Bedrock and uses the MCP tools. See `PRODUCT_FEEDBACK.md`.
- **Open Source:** `guided-intake` is a separate MIT-licensed repository that this project depends on.
- Friction log: `FRICTION_LOG.md`.

## Limits

- Five part types. The geometry is simple on purpose.
- Sessions are kept in memory and lost on restart.
- The tools have no authentication. Do not expose the server to the internet as is.
- Generated files are deleted after `VOICECAD_RETENTION_HOURS`, checked when a new part is finished.

## License

MIT. See `LICENSE`.
