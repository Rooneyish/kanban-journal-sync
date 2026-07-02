#!/home/rooneyish/.venvs/kanban/bin/python3
import os
import json
import requests
import time
import logging
from datetime import date
from simple_term_menu import TerminalMenu

# Files
DB_FILE = os.path.expanduser("~/.minimal_journal.json")
KANBAN_STATE = os.path.expanduser("~/.kanban_state.json")
LOG_FILE = os.path.expanduser("~/.kanban_debug.log")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)

def load_state():
    if os.path.exists(KANBAN_STATE):
        with open(KANBAN_STATE, "r") as f:
            return json.load(f)
    return {"Backlog": [], "In Progress": [], "Done": [], "_last_processed_date": None, "_last_processed_count": 0}

def save_state(state):
    with open(KANBAN_STATE, "w") as f:
        json.dump(state, f)

def get_tasks_from_journal():
    if not os.path.exists(DB_FILE):
        logging.debug("No journal DB file found at %s", DB_FILE)
        return [], None, 0, False

    with open(DB_FILE, "r") as f:
        db = json.load(f)

    if not db:
        logging.debug("Journal DB is empty")
        return [], None, 0, False

    latest_date = sorted(db.keys())[-1]
    entries = db[latest_date]
    entry_count = len(entries)
    try:
        content = "\n\n".join(e["content"] for e in entries)
    except (KeyError, TypeError) as e:
        logging.error("Unexpected journal structure for %s: %s", latest_date, e)
        logging.debug("Raw entry: %s", entries)
        return [], latest_date, 0, False

    logging.debug("Journal content (%s): %s", latest_date, content)

    prompt = (
        "Extract actionable tasks from the journal entry below. "
        "Respond with ONLY a JSON array of strings, nothing else, no markdown fences, "
        "no explanation. If there are no tasks, respond with [].\n\n"
        f"Journal entry:\n{content}"
    )

    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("Could not reach Ollama at %s: %s", OLLAMA_URL, e)
        return [], latest_date, 0, False

    raw = res.json().get("response", "").strip()
    logging.debug("LLM raw output: %s", raw)

    tasks = []
    success = False
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, list):
                tasks = [str(t) for t in parsed]
                success = True

        if not success:
            obj_start = raw.find("{")
            obj_end = raw.rfind("}") + 1
            if obj_start != -1 and obj_end > obj_start:
                parsed = json.loads(raw[obj_start:obj_end])
                if isinstance(parsed, dict):
                    tasks = [k for k, v in parsed.items() if v]
                    success = True

        if success:
            logging.debug("Parsed tasks: %s", tasks)
        else:
            logging.error("No valid JSON array or object found in: %s", raw)
    except Exception as e:
        logging.error("Parsing error: %s | raw was: %s", e, raw)
        tasks = []
        success = False

    return tasks, latest_date, entry_count, success

def launch_kanban_ui():
    state = load_state()
    state.setdefault("_last_processed_date", None)

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        latest_date = sorted(db.keys())[-1] if db else None
        latest_count = len(db[latest_date]) if latest_date else 0
    else:
        latest_date = None
        latest_count = 0

    is_new_day = latest_date and latest_date != state["_last_processed_date"]
    is_new_entry_same_day = (
        latest_date
        and latest_date == state["_last_processed_date"]
        and latest_count != state.get("_last_processed_count", 0)
    )

    if is_new_day or is_new_entry_same_day:
        new_tasks, processed_date, processed_count, success = get_tasks_from_journal()
        if success:
            existing = state["Backlog"] + state["In Progress"] + state["Done"]
            state["Backlog"].extend(t for t in new_tasks if t not in existing)
            if is_new_day:
                state["Done"] = []  # fresh day -- clear out completed tasks
            state["_last_processed_date"] = processed_date
            state["_last_processed_count"] = processed_count
            save_state(state)
        else:
            logging.error(
                "Failed to extract tasks for %s -- will retry on next launch",
                latest_date,
            )

    while True:
        menu_items = []
        mapping = {}

        for section in ["Backlog", "In Progress", "Done"]:
            menu_items.append(f"--- {section.upper()} ---")
            for task in state[section]:
                menu_items.append(task)
                mapping[task] = section

        menu_items.append("Quit")

        menu = TerminalMenu(
            menu_items,
            title="📋 KANBAN BOARD",
            menu_cursor=">> ",
            menu_highlight_style=("standout",),
            clear_screen=True,
        )

        idx = menu.show()
        if idx is None or menu_items[idx] == "Quit":
            break

        selected = menu_items[idx]
        if "---" in selected:
            continue

        source = mapping[selected]
        if source == "Backlog":
            state["Backlog"].remove(selected)
            state["In Progress"].append(selected)
        elif source == "In Progress":
            state["In Progress"].remove(selected)
            state["Done"].append(selected)

        save_state(state)

if __name__ == "__main__":
    launch_kanban_ui()
