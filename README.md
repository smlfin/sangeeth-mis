# Sangeeth MIS Workspace

Automated MIS reports for Sangeeth (RD active accounts, monthly closing, net for the month, deposit outstanding).

| Interface | Command |
|-----------|---------|
| **Web (shareable)** | `streamlit run app.py` |
| **Desktop** | `python snap1.py` |

## Features

- **MIS 1** — Active RD accounts & instalment  
- **MIS 2** — Monthly closing (payment collections)  
- **MIS 3** — Net for the month (MIS 1 − MIS 2)  
- **MIS 4** — Deposit outstanding comparison  

Report dates are chosen in the UI before generation.

## Setup (local)

```bash
cd lco
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and set credentials:

```env
SANGEETH_BASE_URL=http://202.21.37.156/Sangeeth/
SANGEETH_USERNAME=your_username
SANGEETH_PASSWORD=your_password
```

Or set the same variables in the Streamlit sidebar when using the web app.

### Run web app

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

### Run desktop app

```bash
python snap1.py
```

## Share with others (Streamlit Community Cloud)

This gives you a public URL like `https://your-app.streamlit.app`.

1. **Create an empty repo on GitHub** (do not add README/license — you already have code locally).

   - Open [github.com/new](https://github.com/new)
   - Name it e.g. `sangeeth-mis`
   - Choose **Private** if you prefer
   - Click **Create repository**

2. **Connect and push** — replace `YOUR_GITHUB_USERNAME` with your real GitHub username:

   ```bash
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/sangeeth-mis.git
   git branch -M main
   git push -u origin main
   ```

   Example: if your username is `johndoe`, use  
   `https://github.com/johndoe/sangeeth-mis.git`

   If you see `Repository not found`, the repo does not exist yet on GitHub, or the URL username/repo name is wrong.

   To fix a wrong remote:

   ```bash
   git remote remove origin
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/sangeeth-mis.git
   git push -u origin main
   ```

2. Open **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.

3. **New app** → select your repo → **Main file path:** `app.py` → Deploy.

4. **App settings → Secrets** (there is no separate “Environment variables” page on Community Cloud). Paste:

   ```toml
   SANGEETH_BASE_URL = "http://202.21.37.156/Sangeeth/"
   SANGEETH_USERNAME = "your_username"
   SANGEETH_PASSWORD = "your_password"
   ```

   Save — the app reboots. Credentials are read via `st.secrets` / `os.environ` in the app.

5. Share the app URL with colleagues.

### If deploy fails with “installer returned a non-zero exit code”

Push the latest code from this repo. Playwright is **not** installed during the Cloud build anymore; it installs on the first **Generate MIS** click inside the running app.

### If deploy hangs at “Spinning up manager process…” (10+ minutes)

Your logs may show **Python 3.14**. That version is too new for most Streamlit apps and the manager often never starts.

**Fix: delete the app and redeploy with Python 3.12**

1. [share.streamlit.io](https://share.streamlit.io) → open the app → **⋮** → **Delete app**
2. **Create app** again → repo `smlfin/sangeeth-mis`, branch `main`, file `app.py`
3. Click **Advanced settings**
4. **Python version:** choose **3.12** (or **3.11**) — **not 3.14**
5. Paste **Secrets** (username/password)
6. **Deploy**

Build should finish in a few minutes. If logs still show Python 3.14, the wrong version was selected in step 4.

### Important limitations

- The Sangeeth server must be **reachable from where the app runs**. Office/private IPs (e.g. `202.21.37.x`) usually work only on your LAN — run Streamlit on a PC inside that network, or use VPN.
- **Streamlit Cloud** runs on the public internet and often **cannot** reach internal servers. For internal URLs, prefer local `streamlit run app.py` or self-hosted Streamlit on a server inside your network.
- First cloud deploy may take extra time while Playwright installs Chromium.

## Project layout

```
app.py              # Streamlit entry (use for Cloud deploy)
mis_core.py         # Scraping & MIS logic
mis_views.py        # Streamlit dashboard sections
snap1.py            # Desktop Tkinter UI
requirements.txt
.python-version     # Python 3.11 for Streamlit Cloud
.streamlit/         # Theme & secrets example
```

## License

Internal use — keep credentials out of git.
