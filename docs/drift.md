# Code shared with a private setup

This plugin comes from a private set of Herdr scripts. That setup will install this plugin and remove its own copy of the picker. After that, two pieces still live on both sides, and a change to one side must reach the other.

## The title rule

`bin/sessions.py` decides which Claude session a pane runs: `_title` with its `TRANSIENT` titles, `_names`, `_named`, and the title and identity keys of `resolve_all`. The private setup keeps the same rule for its status panel and its sidebar. It also keeps a third key, the working directory, which the picker takes only for a session with no name.

If Claude Code changes how it titles a pane, for example with a new transient title, change both copies.

## The free shell

`running.at_prompt` decides that a shell is at its prompt: Herdr reports the foreground process group of the pane as the shell itself. `bin/busy`, a watcher of the private setup, uses the same rule to mark a pane as busy. If Herdr changes `pane.process_info`, change both.

## The Codex reader

`bin/codex.py` loads `codex_reader.py` of the private setup rather than copying it, and calls `rollout_of` and `meta_of`, so a change of their contract must reach this plugin. The rule for a pane with no session id is its own: the private setup takes the newest rollout of the directory, where the picker refuses more than one, since a panel can afford a wrong guess and a copy cannot.
