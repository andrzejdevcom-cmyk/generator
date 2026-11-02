# 3DAS Letter Maker

- Keep geometry in the Python backend; the viewport and exports consume the same meshes.
- Units are millimetres. Do not replace geometry validation with status-code checks.
- Run `.venv/bin/python -m pytest` and `cd frontend && npm run build` after changes.
- Preserve counters, detached accents, winding, and assembly clearances.
- Never hide rejected LED placements or silently substitute a missing font.
- Do not claim slicer or physical print compatibility without testing it.
- Work in the existing isolated checkout; do not create worktrees unless requested.
- Do not use sub-agents unless the user explicitly requests delegation.
