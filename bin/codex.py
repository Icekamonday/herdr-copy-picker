"""Which Codex session a pane runs, and the answers in its rollout.

The reader of Codex sessions is a module of another repository, and the
picker keeps no copy of it. A file of the configuration names it, and only a
Codex pane needs it, so a Claude pane works without it.
"""

import glob
import importlib.util
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sessions

KIND = 'codex'                # what Herdr reports as the agent of a Codex pane
RECENT = 7 * 86400            # an older rollout runs in no pane
INTERACTIVE = ('cli',)        # the source of a TUI session; exec is a run
SESSION_ID = re.compile(r'[0-9A-Za-z-]+')  # it goes into a glob
# what Codex records as a user message and nobody typed
INJECTED = re.compile(r'\s*<([a-z_]+)>.*</\1>\s*', re.DOTALL)
NEEDED = ('CODEX_HOME', 'rollout_of', 'meta_of')


def reader_file():
    return os.path.join(os.path.dirname(sessions.sources_file()), 'codex-reader')


def load_reader():
    """The reader module, from the very file that the configuration names.

    It is not put on the path: its directory holds modules with the names of
    those of the picker.
    """
    config = reader_file()
    try:
        with open(config, encoding='utf-8') as fp:
            path = os.path.expanduser(fp.read().strip())
    except (OSError, ValueError):
        path = ''
    if not path:
        raise sessions.NoTranscript(f'write the path of codex_reader.py in {config}')
    spec = importlib.util.spec_from_file_location('codex_reader', path)
    if spec is None:
        raise sessions.NoTranscript(f'{path} is no Python file: fix {config}')
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as why:  # importing another repository's code can raise anything
        raise sessions.NoTranscript(f'cannot load {path}: {why}. Fix {config}') from why
    if not all(hasattr(module, name) for name in NEEDED):
        raise sessions.NoTranscript(f'{path} is not the Codex reader: fix {config}')
    return module


def _session_id(pane):
    sid = (pane.get('agent_session') or {}).get('value')
    return sid if isinstance(sid, str) and SESSION_ID.fullmatch(sid) else None


def _of_directory(reader, cwd, claimed):
    """The interactive rollouts of a directory, recent, that no pane holds."""
    if not cwd:
        return []
    here, since = os.path.realpath(cwd), time.time() - RECENT
    found = []
    for path in glob.glob(os.path.join(reader.CODEX_HOME, 'sessions', '*', '*', '*',
                                       'rollout-*.jsonl')):
        try:
            if path in claimed or os.path.getmtime(path) < since:
                continue
        except OSError:
            continue
        meta = reader.meta_of(path)
        if meta.get('source') in INTERACTIVE \
                and os.path.realpath(meta.get('cwd') or '') == here:
            found.append(path)
    return found


def find(pane, panes):
    """The rollout of the session that a pane runs.

    The id that Herdr holds names it. Without one, the directory decides, but
    only when it leaves a single rollout: what the picker copies must come
    from this session and no other.
    """
    reader = load_reader()
    sid = _session_id(pane)
    path = reader.rollout_of(sid) if sid else None
    if path:
        return path
    claimed = {reader.rollout_of(other) for other in map(_session_id, panes) if other}
    found = _of_directory(reader, pane.get('cwd'), claimed)
    if len(found) == 1:
        return found[0]
    why = f'{len(found)} sessions ran in this directory' if found else 'no rollout carries it'
    raise sessions.NoTranscript(
        f'send a prompt in this Codex session, then press the key again: {why}')


def _texts(payload, kind):
    return [part['text'] for part in payload.get('content') or []
            if isinstance(part, dict) and part.get('type') == kind and part.get('text')]


def answers(path, cut_prompt):
    """The answers of a rollout, oldest first, in the form of those of Claude.

    Each message that a person typed opens a turn, and each message of the
    assistant joins the turn open then, commentary as well as the final
    answer. The tail is read and cut as for a transcript, and cut_prompt
    stands for the prompt of a turn whose start it lost.
    """
    read, cut = sessions.tail(path, sessions.FIND_WINDOW)
    lines = read.split(b'\n')
    found, turn = [], None
    if cut:
        lines, turn = lines[1:], {'prompt': cut_prompt, 'messages': []}
        found.append(turn)
    for raw in lines:
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get('type') != 'response_item':
            continue
        payload = record.get('payload')
        if not isinstance(payload, dict) or payload.get('type') != 'message':
            continue
        if payload.get('role') == 'user':
            typed = [text for text in _texts(payload, 'input_text')
                     if not INJECTED.fullmatch(text)]
            if typed:
                turn = {'prompt': '\n'.join(typed).strip('\n'), 'messages': []}
                found.append(turn)
        elif payload.get('role') == 'assistant' and turn is not None:
            texts = _texts(payload, 'output_text')
            if texts:
                turn['messages'].append('\n\n'.join(texts))
    return [answer for answer in found if answer['messages']]
