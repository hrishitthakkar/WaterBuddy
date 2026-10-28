"""Logic tests for WaterBuddy using Streamlit's AppTest.

Run with:  python -m pytest tests   (or)   python tests/test_app.py
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def fresh_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception, at.exception
    return at


def total(at: AppTest) -> int:
    return sum(e["ml"] for e in at.session_state.log)


def test_defaults():
    at = fresh_app()
    assert at.session_state.age_group == "Teens (13–18)"
    assert at.session_state.goal == 2100
    assert at.session_state.log == []


def test_logging_buttons():
    at = fresh_app()
    at.button(key="log250").click().run()
    at.button(key="log100").click().run()
    at.button(key="log500").click().run()
    assert total(at) == 850
    assert [e["ml"] for e in at.session_state.log] == [250, 100, 500]
    assert all(len(e["time"]) == 5 for e in at.session_state.log)  # HH:MM timestamps


def test_custom_amount_cups_and_ml():
    at = fresh_app()
    at.number_input(key="custom_amount").set_value(2.0)
    at.radio(key="custom_unit").set_value("cups")
    at.button(key="FormSubmitter:custom_form-Add drink").click().run()
    assert total(at) == 500
    at.number_input(key="custom_amount").set_value(330.0)
    at.radio(key="custom_unit").set_value("ml")
    at.button(key="FormSubmitter:custom_form-Add drink").click().run()
    assert total(at) == 830


def test_age_change_updates_goal():
    at = fresh_app()
    at.selectbox(key="age_group").set_value("Adults (19–50)").run()
    assert at.session_state.goal == 2500
    at.selectbox(key="age_group").set_value("Kids (6–12)").run()
    assert at.session_state.goal == 1600


def test_custom_goal():
    at = fresh_app()
    at.number_input(key="goal").set_value(3000).run()
    assert at.session_state.goal == 3000
    for _ in range(3):
        at.button(key="log500").click().run()
    # 1500 / 3000 = 50%, 1500 left = 6 glasses
    text = " ".join(m.value for m in at.markdown)
    assert "1,500" in text and "50%" in text and "6</b> glasses left" in text
    # A custom goal survives other reruns until the age group changes
    at.button(key="log100").click().run()
    assert at.session_state.goal == 3000


def test_undo():
    at = fresh_app()
    at.button(key="log250").click().run()
    at.button(key="log500").click().run()
    at.button(key="undo").click().run()
    assert [e["ml"] for e in at.session_state.log] == [250]
    at.button(key="undo").click().run()
    assert at.session_state.log == []
    assert at.button(key="undo").disabled


def test_reset_and_last_day():
    at = fresh_app()
    at.button(key="log500").click().run()
    at.button(key="reset").click().run()
    assert at.session_state.log == []
    assert at.session_state.last_day["total"] == 500


def test_auto_reset_on_new_date():
    at = fresh_app()
    at.button(key="log250").click().run()
    at.session_state.day = "2000-01-01"  # pretend the log is from an old day
    at.run()
    assert at.session_state.log == []
    assert at.session_state.day != "2000-01-01"


def test_goal_reached_balloons_once():
    at = fresh_app()
    at.selectbox(key="age_group").set_value("Kids (6–12)").run()  # 1600 ml
    for _ in range(3):
        at.button(key="log500").click().run()
    assert not at.session_state.celebrated
    at.button(key="log100").click().run()  # 1600 ml = 100%
    assert at.session_state.celebrated
    assert "You did it" in " ".join(m.value for m in at.markdown)


if __name__ == "__main__":
    import sys
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if failed else 0)
