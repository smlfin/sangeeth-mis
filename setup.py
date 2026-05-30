"""Install deps for Streamlit Cloud; skip Chromium download until first app use."""
import os

os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

from setuptools import setup

setup(
    name="sangeeth-mis",
    version="0.1.0",
    install_requires=[
        "streamlit==1.41.1",
        "pandas==2.2.3",
        "xlrd==2.0.1",
        "openpyxl==3.1.5",
        "playwright==1.49.1",
    ],
)
