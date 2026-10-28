# WaterBuddy 💧

A daily hydration tracker built with Python and Streamlit for IBCP CRS AI (FA-2).

The whole screen is the water bottle: as you log drinks, a water layer rises
up behind the app, with drifting waves and bubbles. Drippy, the droplet mascot,
cheers you on, and his mood changes as you hit each milestone.

## Features

### Core
- **Age groups** with a suggested daily goal: Kids (6–12) 1,600 ml, Teens (13–18) 2,100 ml,
  Adults (19–50) 2,500 ml, Older adults (51–64) 2,400 ml, Seniors (65+) 2,000 ml
- **Editable goal**: the goal is filled in from your age group and you can change it.
  Picking a new age group resets the goal to that group's suggestion
- **Quick logging**: a big +250 ml button, plus +100 ml, +500 ml and a custom amount in ml or cups
- **Start a new day** button, and an automatic reset when the date changes (India time, Asia/Kolkata)
- **Live calculations** in separate functions: total intake, ml remaining, % of goal, glasses left
  (remaining ÷ 250, rounded up)
- **Progress bar** with milestone dots at 25 / 50 / 75 / 100% that turn gold as you pass them
- **Drippy the mascot** and a motivational message that change at 0, 25, 50, 75 and 100%,
  written in a different tone for each age group
- **Privacy-friendly**: everything lives in `st.session_state`. Nothing is saved to a file or database

### Extras
- Standard age target vs your own goal, side by side with comparison bars
- Cups ↔ ml converter in the sidebar (1 cup = 250 ml)
- Random hydration tip with a "Show another tip" button
- Undo last drink
- Today's drinks log with timestamps
- Balloons the first time you reach your goal, and an end-of-day summary
- Water turns sea-green at 100%
- Works on phones and respects the "reduce motion" accessibility setting

## Run it locally

You need Python 3.10 or newer.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Run the tests

```bash
pip install pytest
python -m pytest tests
```

The tests use `streamlit.testing.v1.AppTest` to check logging, the age group → goal link,
custom goals, custom amounts, undo, manual reset and the automatic new-day reset.

## Project structure

```
app.py                  all app code, split into sections:
                        config/data, session_state helpers, calculations,
                        visual components, CSS, page layout
requirements.txt        streamlit (1.45+ for keyed containers) and tzdata
.streamlit/config.toml  light theme colours
tests/test_app.py       AppTest logic tests
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repo.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app** → **Deploy a public app from GitHub**.
4. Pick the repo, branch `main` and main file `app.py`, then click **Deploy**.
