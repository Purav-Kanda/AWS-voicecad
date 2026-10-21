# Architecture

voicecad has two repositories.

- **guided-intake** (separate, MIT): a small library that turns "ask the user for missing details" into plain, testable code. It knows nothing about 3D printing.
- **voicecad**: an MCP server that uses guided-intake to ask for dimensions, then builds and checks a 3D model.

```
 voice assistant / browser page
            |  (speech to text, then text)
            v
   Strands agent on Amazon Bedrock          <- agent.py (demo only)
            |  MCP over Streamable HTTP
            v
   voicecad MCP server                      <- server.py (composition root)
      |-- guided-intake tools: list_specs, start_intake, submit_answers, review, finish
      |-- preview_part
      |
      |   Catalog  ->  Part  ->  Spec (questions + rules)  +  build() (geometry)
      |   Finisher ->  checks the real mesh, writes STL files
      v
   out/*.stl, out/*.png
```

## The idea that matters

A language model is good at conversation and bad at remembering which of eleven measurements it has not asked about yet. So the conversation state is code, not prompt text.

- The **spec** lists every field, its unit, limits, default, and rules.
- The **session** knows which field is next, skips fields that do not apply, converts "4 inches" to millimeters, and re-checks every rule after each answer.
- The **assistant** only decides how to phrase the next question and how to read the user's reply.

Because of this, the same behavior is unit tested without any model call.

## Modules

| Module | One job |
| --- | --- |
| `parts/<name>.py` | One kind of part: its questions, its rules, its geometry |
| `parts/registry.py` | The list of parts on offer |
| `catalog.py` | Builds each part's spec for the chosen printer and runs builds by name |
| `printer.py` | `PrinterProfile` (bed size, minimum wall) and presets |
| `config.py` | `Settings`, read from the environment once |
| `geometry.py` | Pure mesh helpers: block, join, carve, wedge, tube, post |
| `checks.py` | Rules that apply to every part: bed fit, thin walls, watertight mesh |
| `files.py` | Safe file names and deleting old files |
| `uploads.py` | `UploadStore`: checks and keeps uploaded STL files, hands them out by id only |
| `build.py` | `Finisher`: build, check, write files, return a spoken summary |
| `server.py` | Wires everything. The only module that knows all the others |
| `agent.py`, `offline.py`, `web.py` | The demo assistant (Bedrock or the no-model stand-in) and its page. The MCP server does not import them |

## Design decisions

Each entry: the decision, why, and what it costs.

1. **Each part is one module (open/closed principle).**
   Why: adding a part touches one new file and one line in `registry.py`. Nothing that already works is edited.
   Tradeoff: some repeated shape in the `make_spec` functions. I accepted that over a shared base class that would couple the parts.

2. **The printer is passed in, not a global constant (dependency injection).**
   Why: the first version hard coded a 220 by 220 by 250 bed, and the stand rule used a guessed depth of 120 mm. Now rules ask a `PrinterProfile`, and the stand computes its real depth (59 mm by default). A test pins this: a 60 mm bed edge accepts the default stand and a 58 mm edge rejects it.
   Tradeoff: every `make_spec` takes a profile argument.

3. **Settings are read in one place (config at the edge).**
   Why: modules deeper in the program never touch `os.environ`, so tests pass a plain dictionary.
   Tradeoff: a few more lines in `server.py`.

4. **`server.py` is the composition root.**
   Why: it is the only place where concrete choices (which parts, which printer, where files go) meet. Everything else receives what it needs.
   Tradeoff: tests that want a different setup must build the server themselves, which they do through `create_server(settings, catalog)`.

5. **Geometry is pure functions (single responsibility, easy testing).**
   Why: `geometry.py` has no printer, file or session knowledge, so each helper is tested alone. The wedge winding bug would have been hard to find any other way.
   Tradeoff: parts pass meshes around instead of calling methods on a builder object.

6. **Errors are handled at the boundary.**
   Why: a failed boolean operation inside a part should become a spoken message ("I could not build that shape"), not a crashed server. `Finisher` catches it, logs the traceback, and returns `ok: false`. File names from the network go through `safe_output_path`, which rejects slashes, wrong suffixes and anything that resolves outside the output folder.
   Tradeoff: a broad `except` in one place. It is logged, and tested.

7. **Rules run on questions and again on the finished mesh.**
   Why: early rules ("walls too thin") let the assistant fix a problem while the user is still talking. The final mesh check (`mesh_issues`) catches what rules cannot see, such as a non-watertight result.
   Tradeoff: the same bed rule appears twice, once on the planned size and once on the real size. They share one function, `bed_issues`.

8. **Sessions live in memory behind a lock.**
   Why: simplest thing that is correct for one server process. `SessionStore` operations are thread safe and capped.
   Tradeoff: sessions are lost on restart, and one server process only.

9. **An upload is reached only through an id the server made (path safety).**
   Why: the assistant passes the id as text, so a name like `../../x` must never reach the disk. `UploadStore` makes ids as 12 hex digits, accepts only that shape, and refuses unreadable, flat, oversized or unrepairable files before anything else sees them.
   Tradeoff: no original file names on disk, and a stricter rule than most slicers. A model with holes that cannot be patched is refused up front instead of failing at the end.

10. **Resizing scales a model and never edits it.**
    Why: a mesh has no features to move. Scaling is honest and cheap, and the rules warn where it hurts: uneven stretch (holes turn oval), strong shrink (walls thin), and sizes that look like the wrong unit. Anything cleverer needs feature detection, which is a different project.
    Tradeoff: no "keep the screw holes the same size". The part says so in its warnings.

11. **A part that needs a file is given a loader, not a path (dependency injection again).**
    Why: `Part.build` does no I/O. `custom_model.make_part(load)` receives `UploadStore.load`, so tests run the part against an in-memory loader and the part never learns where files live.
    Tradeoff: the registry takes one optional argument, and the part only exists when uploads do.

## How it is tested

| Layer | Test |
| --- | --- |
| Geometry | Volumes and points inside or outside the mesh (`test_build.py`, `test_new_parts.py`) |
| Rules | Each rule has a case that triggers it and one that does not (`test_rules.py`) |
| Whole space | Seeded random designs: whatever the rules accept must build, and be watertight (`test_sweep.py`) |
| Protocol | The ASGI app driven over MCP JSON-RPC, protocol 2025-11-25 (`test_server_e2e.py`) |
| Agent side | The Strands `MCPClient` against a real server on a real socket, no model (`test_strands_link.py`) |
| Demo page | Routes with a stub assistant (`test_web.py`), and the real page in headless Chromium (`test_ui.py`) |
| Offline stand-in | Scripted conversations (`test_offline.py`) |
| Upload and resize | Store checks, path safety, sizing rules, the real build, the upload route, MCP, offline chat and a browser run (`test_custom_model.py`, `test_ui.py`) |

Not tested: a live Bedrock model, and a real Alexa+ device.

## Add a part in five steps

1. Create `src/voicecad/parts/my_part.py`.
2. Write `make_spec(profile) -> Spec` with `Field`s and `Check`s. Use `checks.bed_issues` for the print bed.
3. Write `build(answers) -> Built`. Return one mesh per printed piece, notes for the user, and `copies={"name": 2}` if a piece is printed more than once.
4. End the file with `PART = Part(NAME, make_spec, build)`.
5. Add `my_part.PART` to `default_parts()` in `parts/registry.py`.

Then add a test next to `tests/test_new_parts.py`: one for the geometry (volume or a point inside or outside the mesh), one for each rule.

## What is not covered

- No authentication on the MCP endpoint. Do not expose it to the internet as is.
- Not tested on an Alexa+ device, and not tested against a live Bedrock model in this build environment.
- Printability checks are rules of thumb and a watertight test. They are not a slicer.
