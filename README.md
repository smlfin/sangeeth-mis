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

1. **Push this folder to GitHub** (private repo recommended — no passwords in code).

   ```bash
   git init
   git add .
   git commit -m "Initial Sangeeth MIS app"
   git remote add origin https://github.com/YOUR_USER/sangeeth-mis.git
   git push -u origin main
   ```

2. Open **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.

3. **New app** → select your repo → **Main file path:** `app.py` → Deploy.

4. **App settings → Secrets** — paste (from `.streamlit/secrets.toml.example`):

   ```toml
   SANGEETH_BASE_URL = "http://202.21.37.156/Sangeeth/"
   SANGEETH_USERNAME = "your_username"
   SANGEETH_PASSWORD = "your_password"
   ```

5. Share the app URL with colleagues.

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
packages.txt        # Linux libs for Playwright on Streamlit Cloud
.streamlit/         # Theme & secrets example
```

## License

Internal use — keep credentials out of git.
