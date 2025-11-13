#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SubagentStop Hook - Sub-agent completion notifier (v20.1)
Trigger: When sub-agent completes response
Responsibility: Notify user that sub-agent exploration is complete and ready to implement
"""

import os
import sys
import json
import io

# Windows encoding fix
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import notification module
try:
    from vscode_notify import notify_info
except ImportError:
    def notify_info(msg, detail=""):
        pass

def main():
    try:
        # Read hook input
        hook_input = json.load(sys.stdin)

        session_id = hook_input.get('session_id', '')
        transcript_path = hook_input.get('transcript_path', '')

        # Parse sub-agent information
        agent_type = "Exploration sub-agent"

        if transcript_path and os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:
                        data = json.loads(line)
                        if 'description' in data:
                            agent_type = data['description']
                            break
            except:
                pass

        # Desktop notification
        notify_info(
            u"✅ {} completed".format(agent_type),
            "Exploration results returned, ready to implement"
        )

        # Allow continue
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        # On exception, allow continue
        sys.stderr.write("[ERROR] SubagentStop Hook execution exception: {}\n".format(str(e)))
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

if __name__ == '__main__':
    main()
