from datetime import datetime, timezone
import os
import io
import difflib


def _normalize_text(s: str) -> str:
    # Simple fixes: convert tabs to 4 spaces, strip trailing whitespace, ensure newline at EOF
    lines = s.splitlines()
    new_lines = [line.replace("\t", "    ").rstrip() for line in lines]
    return "\n".join(new_lines) + "\n"


def generate_fix_plan_for_path(root_path: str):
    fixes = []
    for dirpath, _, filenames in os.walk(root_path):
        for fn in filenames:
            if fn.endswith(('.py', '.md', '.txt', '.cfg', '.ini', '.yml', '.yaml')):
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        orig = f.read()
                except Exception:
                    continue

                new = _normalize_text(orig)
                if new != orig:
                    fixes.append({'path': os.path.relpath(fp, root_path), 'original': orig, 'updated': new})

    plan = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'fix_count': len(fixes),
        'fixes': fixes,
        'status': 'plan_created',
    }
    return plan


def generate_fix_plan(review_or_path):
    # Backwards compatible: if argument is dict (a report), try to find path
    if isinstance(review_or_path, dict):
        path = review_or_path.get('path') or review_or_path.get('repo_path') or '.'
        return generate_fix_plan_for_path(path)
    elif isinstance(review_or_path, str):
        return generate_fix_plan_for_path(review_or_path)
    else:
        return {'generated': datetime.now(timezone.utc).isoformat(), 'fix_count': 0, 'fixes': [], 'status': 'no_action'}


def apply_fix_plan(fix_plan, target_root=None):
    # Apply the fixes to files under target_root if provided; otherwise simulate and return patches
    applied = []
    for item in fix_plan.get('fixes', []):
        path = item['path']
        updated = item['updated']
        if target_root:
            dest = os.path.join(target_root, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(updated)
            applied.append({'path': path, 'action': 'written'})
        else:
            # produce a unified diff for preview
            orig = item.get('original', '').splitlines(keepends=True)
            new = updated.splitlines(keepends=True)
            diff = ''.join(difflib.unified_diff(orig, new, fromfile='a/'+path, tofile='b/'+path))
            applied.append({'path': path, 'patch': diff})

    return {'status': 'applied' if target_root else 'preview', 'changes': applied}
