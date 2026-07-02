# Kanban Journal Sync

A terminal-based Kanban board that automatically extracts actionable tasks
from a daily journal using a local LLM (via [Ollama](https://ollama.com))
and organizes them into Backlog / In Progress / Done columns.

## How it works

1. You keep a daily journal in `~/.minimal_journal.json` (managed by a
   separate journaling tool/script).
2. On launch, `journal_sync.py` checks whether there's new journal content
   for the current date that hasn't been processed yet.
3. If so, it sends the day's journal text to a local model
   (`qwen2.5-coder:7b` via Ollama) with a prompt asking it to extract
   actionable tasks as a JSON array.
4. Extracted tasks are added to the **Backlog** column, skipping anything
   already present (exact string match).
5. An interactive terminal menu (via
   [`simple_term_menu`](https://github.com/IngoMeyer441/simple-term-menu))
   lets you move tasks: Backlog → In Progress → Done.
6. State persists in `~/.kanban_state.json` between runs.

## Key behaviors

- **Re-extraction is triggered by either a new date or a new journal entry
  on the same date** — so journaling multiple times in one day (e.g. once
  in the morning, once later) will pick up new tasks without needing a new
  calendar day.
- **All entries for the current date are read**, not just the most recent
  one, so nothing gets missed if you journal more than once per day.
- **Done tasks are cleared automatically at the start of a new day**
  (no archive is kept — this is intentional, see project history).
- **Task extraction handles both array and object-shaped LLM output.**
  Some models occasionally return `{"task": true, ...}` instead of a JSON
  array despite the prompt; both shapes are parsed.
- **A failed extraction (Ollama unreachable, bad JSON, etc.) does not mark
  the day as processed** — it will retry on the next launch rather than
  silently losing that day's tasks.

## Files

| File | Purpose |
|---|---|
| `journal_sync.py` | Main script: extraction logic + Kanban TUI |
| `launch_sticky.sh` | Launches `journal_sync.py` inside a dedicated Alacritty window |
| `~/.minimal_journal.json` | Journal data (not tracked in this repo) |
| `~/.kanban_state.json` | Kanban board state (not tracked in this repo) |
| `~/.kanban_debug.log` | Debug log for extraction runs (not tracked in this repo) |

## Setup

1. Requires Python 3, [Ollama](https://ollama.com) running locally with
   `qwen2.5-coder:7b` pulled, and a terminal emulator (this was built
   around Alacritty, but any terminal works if you run `journal_sync.py`
   directly).
2. Create a virtual environment and install dependencies:
```bash
   python3 -m venv ~/.venvs/kanban
   source ~/.venvs/kanban/bin/activate
   pip install simple_term_menu requests
```
3. Update the shebang in `journal_sync.py` and the interpreter path in
   `launch_sticky.sh` to point at your venv's Python if it differs from
   `~/.venvs/kanban/bin/python3`.
4. (Optional) To auto-launch on login, add an
   [XDG autostart](https://specifications.freedesktop.org/autostart-spec/autostart-spec-latest.html)
   entry in `~/.config/autostart/` pointing `Exec=` at `launch_sticky.sh`.

## Known limitations

- Task dedup is exact-string-match only — the LLM's non-deterministic
  phrasing across runs can produce near-duplicate tasks (e.g. "Pivot to
  BERT-based classifier" vs "Pivot from Seq2Seq to BERT-based classifier")
  that aren't automatically merged.
- No distinction is made between work tasks and personal/leisure items —
  anything the model judges "actionable" gets extracted.
- Done column has no history/archive; completed tasks are lost once
  cleared at the start of a new day.
