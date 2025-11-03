# Textual `/models` Selector – Implementation Notes

This document explains how the Textual UI drives model selection after the April 2025 refresh. It describes the user-facing flow, the widgets involved, and the plumbing between the UI and the REPL/runtime services. The controller lives in `swecli/ui_textual/controllers/model_picker_controller.py`.

---

## 1. Overview

The `/models` command now runs entirely inside the Textual conversation log. Instead of launching a prompt_toolkit modal or asking for numeric input, it renders Rich panels inline and republishes the active panel whenever the user navigates. The selector understands three stages:

1. **Slot selection** – Choose between the Normal, Thinking, and Vision model slots (plus Finish/Cancel options).
2. **Provider selection** – Filter providers that have models capable of filling the chosen slot.
3. **Model selection** – Choose a specific model for that provider/slot combination.

All stages share the same mechanics:

- Arrow keys (`↑`/`↓`) highlight the next entry.
- `Enter` confirms the current selection.
- `Esc` or `Ctrl+C` cancels the entire picker.
- `B` backs out to the previous stage.
- `S` commits any staged selections during the slot stage.
- Numeric shortcuts (`1`, `2`, …) still work, but arrows are the primary control path.

---

## 2. UI Composition

### 2.1 Conversation Panels

- Panels are rendered via `ModelPickerController._post_model_panel()` which inserts the Rich panel and remembers the index of the first inserted line in `self.state["panel_start"]`.
- When the panel needs to re-render, the stored index is used to truncate the conversation log so only one panel is visible at a time.
- Each row is a `Table.grid()` row with:
  - A pointer cell (`❯`) highlighted for the active row.
  - The human-readable label (slot/provider/model name).
  - A secondary column for context (current configuration, provider detail, or model context size).
- Provider panels only render up to 7 rows at a time; `…` rows indicate additional providers above/below the window so the picker stays compact.

### 2.2 State Machine

`ModelPickerController.state` captures the entire state:

| Field            | Purpose                                                |
|------------------|--------------------------------------------------------|
| `stage`          | `"slot"`, `"provider"`, or `"model"`                   |
| `registry`       | Cached registry handle (avoids repeated disk loads)    |
| `slot`           | The currently selected slot (`normal`/`thinking`/`vision`) |
| `providers`      | Provider entries matching the slot                     |
| `models`         | Model entries for the selected provider                |
| `slot_index`     | Highlight index for the slot table                     |
| `provider_index` | Highlight index for the provider table                 |
| `model_index`    | Highlight index for the model table                    |
| `panel_start`    | Line index of the active panel in the conversation log |
| `pending`        | Dict of staged selections awaiting save                |

Navigation helpers (`move()`, `confirm()`, `back()`, and `handle_input()`) mutate this state and call the appropriate render method.

---

## 3. Input Handling

`ChatTextArea._on_key()` intercepts keys while the picker is active:

- `↑`/`↓` call `_model_picker_move(±1)` on the controller.
- `Enter` awaits `_model_picker_confirm()`.
- `Esc` or `Ctrl+C` triggers `_model_picker_cancel()`.
- Printable characters (numbers, letter shortcuts) forward to `_handle_model_picker_input()` so the numeric shortcuts still function.
- When you stage a model selection, the picker jumps back to the slot list and displays the staged provider/model with a `(pending)` suffix until you choose `Save models`.

Once the picker exits, `ModelPickerController.end()` clears state and optionally removes the panel (unless keeping it around for the Save summary).

---

## 4. Wiring Back to the REPL

- `TextualRunner` passes two callbacks into `create_chat_app()`:
  - `on_model_selected(slot, provider_id, model_id)` – calls `ConfigCommands._switch_to_model()` on a worker thread.
  - `get_model_config()` – returns a Rich snapshot used to pre-populate the panels and summary table.
- After a successful save, `_refresh_ui_config()` reloads the app config and updates both the status bar and footer.
- Errors from `_switch_to_model()` surface in the conversation via `notify_processing_error()` so the user sees a red bullet.

---

## 5. Catalog Sourcing

- `ModelRegistry` now augments the local JSON files with the [Models.dev](https://models.dev) catalog that OpenCode ships against.
- We skip the Fireworks entry so our curated Fireworks metadata and defaults remain authoritative.
- Caching lives under `~/.swecli/cache/models.dev.json`; set `SWECLI_DISABLE_REMOTE_MODELS=1` to stay offline or `SWECLI_MODELS_DEV_PATH` to point at a local snapshot when testing.
- As soon as the registry loads the additional providers, the picker surfaces them automatically, so the `/models` UI stays in sync with the latest OpenCode model roster.

---

## 6. Save & Validation Phase

- Stage as many model changes as you like; nothing persists until you choose **Save models** from the slot list.
- Save iterates the staged selections, calls the existing `ConfigCommands._switch_to_model()` backend (which performs its own validation), and surfaces per-slot success/failure messages in the conversation log.
- On success, the backend refreshes the status bar/footer via the runner callbacks; failed slots remain staged so the user can adjust and retry.

---

## 7. Missing Model Handling

Sending a message now validates the Normal model before calling into the REPL:

- `TextualRunner._run_query()` checks `config.get_model_info()`.
- If it returns `None` (model deleted or misconfigured), the UI posts a red bullet error advising the user to run `/models`.
- No backend call is made, so the spinner stops immediately.

---

## 8. Conversation Error Styling

- Conversation errors render as `⦿ <text>` in bold red, matching the new send-failure messages.
- The spinner stop logic (`ConversationLog.add_error()`) ensures the status bar resets when an error occurs.

---

## 9. Testing Notes

Manual checklist:

1. `/models` → arrow through slots, press `Enter` to open provider list.
2. Arrow through providers, `Enter` to view models, `B` to back out.
3. Select a model → dialog should close, footer/status update instantly, and the summary panel should be replaced with the slot picker.
4. Delete the configured model from the registry (simulate) and send a message → you should see `⦿ Send failed: configured Normal model is missing. Run /models to choose a valid model.` with no hang.

The build currently relies on manual testing; no automated tests cover the picker yet.

---

## 10. File Touchpoints

| File                                    | Purpose                                                                       |
|-----------------------------------------|-------------------------------------------------------------------------------|
| `swecli/ui_textual/chat_app.py`         | State machine, Rich panels, keyboard handling, red bullet error formatting   |
| `swecli/ui_textual/runner.py`           | Callback wiring, config refresh, missing-model guard                         |
| `swecli/repl/commands/config_commands.py` | Saves config, calls `refresh()` instead of `invalidate()`                    |

This structure keeps the UI self-contained while still reusing the REPL’s persistence logic.
