from backend.agents.fix_agent import generate_fix_plan, apply_fix_plan


def test_fix_agent_generates_fixes(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / "a.py").write_text('def f():\n\tprint("hi")  \n')

    plan = generate_fix_plan(str(d))
    assert plan["fix_count"] >= 1
    assert plan["status"] == "plan_created"

    preview = apply_fix_plan(plan)
    assert preview["status"] == "preview"
    assert preview["changes"]
    assert any("patch" in change for change in preview["changes"])

    applied = apply_fix_plan(plan, target_root=str(d))
    assert applied["status"] == "applied"
    text = (d / "a.py").read_text()
    assert "\t" not in text
    assert text.endswith("\n")
