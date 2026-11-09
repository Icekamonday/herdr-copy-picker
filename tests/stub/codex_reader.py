"""A stand-in for the module that the picker loads for a Codex pane: the two
functions it calls and the root it searches, with the same contract."""

import glob
import json
import os

CODEX_HOME = os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')


def rollout_of(sid):
    found = glob.glob(os.path.join(CODEX_HOME, 'sessions', '*', '*', '*',
                                   f'rollout-*-{sid}.jsonl'))
    return max(found, key=os.path.getmtime) if found else None


def meta_of(path):
    with open(path, encoding='utf-8') as fp:
        for line in fp:
            record = json.loads(line)
            if record.get('type') == 'session_meta':
                return record.get('payload') or {}
    return {}
