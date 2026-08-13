# TODO: Voice-Prompted Agent Learning

## Done

- [x] **Teach the LLM to extract arguments** — the system prompt now instructs the LLM to include an `"argument"` field (`null` or `"remainder"`). When `"remainder"`, the shell command uses `{q}` as a placeholder and the handler code substitutes the extracted speech remainder at runtime. The `argument` field is persisted in `custom_commands.json` and passed through `matcher.add_command()` so the matcher extracts the remainder on future invocations.

- [x] **LLM command proposal flow** — when a wake word utterance doesn't match a known command, send it to the local LLM which returns a JSON action. If it's a system action, propose a shell command.
- [x] **Voice confirmation** — instead of `input()`, set a `pending_cmd` state. The TTS says "Run this command?" and listens for "yes" or "no" via the normal speech pipeline.
- [x] **Runtime registration** — approved commands are `exec()`'d into globals, registered in `HANDLER_MAP`, and hot-added to the semantic matcher via `matcher.add_command()`. The next utterance hits the matcher — no LLM round trip.
- [x] **Persistence** — approved commands save to `~/.config/whisper_dictation/custom_commands.json`. On startup, `load_custom_commands()` execs all saved handlers and adds them to the matcher.
- [x] **Wake-word gating** — the proposal flow only fires on wake words ("Computer", "Samantha", "Peter"), so normal dictation never hits the LLM.
- [x] **Safe rejection** — "no" clears pending, "never mind" dismisses, unrecognized replies re-prompt. Wake-word utterances that aren't actions are silently consumed (not typed as dictation).
- [x] **`initialize_project` command** — voice command ("Computer, initialize project") scans all non-hidden text files (depth ≤ 2) for shebangs, classes, functions, docstrings, service URLs/ports, and dependencies; generates or updates `AGENTS.md` with a comprehensive project guide.
- [x] **`project_scanner.py` module** — extracted scanner logic into a standalone, importable module (`is_text_file`, `find_text_files`, `build_file_tree`, `initialize_project`) with a `__main__` guard for CLI use.

## Next
- [ ] **Handler beyond shell** — the proposal flow only generates `subprocess.Popen()` handlers. Support proposing Python code that uses the app's own APIs (`pyautogui.write`, `open_app`, etc.) or orchestrates multiple steps.
- [ ] **List learned commands** — "Computer, what commands do you know?" reads back the custom command list via TTS.
- [ ] **Multi-turn proposal** — let the LLM refine a command if the user says "no, with a 60 second timeout instead" rather than starting over.
- [_] **Create a tool** — "Computer, create a tool to touch a file when I say touch followed by the file name." Add an agent behavior to have LLM create the described tool in the tools directory ~/.config/whisper_dictation/tools/[tool name].json