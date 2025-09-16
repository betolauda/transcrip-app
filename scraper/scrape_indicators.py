import sqlite3
import requests
from datetime import datetime

DB_PATH = "scraper/indicators.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            value REAL,
            date TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_indicator(name, value, source):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO indicators (name, value, date, source)
        VALUES (?, ?, ?, ?)
    """, (name, value, datetime.utcnow().isoformat(), source))
    conn.commit()
    conn.close()

# ---------------- Scrapers ----------------

def scrape_dollar():
    """Official & Blue dollar from Bluelytics API"""
    url = "https://api.bluelytics.com.ar/v2/latest"
    res = requests.get(url).json()
    official = res["oficial"]["value_avg"]
    blue = res["blue"]["value_avg"]
    insert_indicator("USD_ARS_oficial", official, url)
    insert_indicator("USD_ARS_blue", blue, url)

def scrape_inflation():
    """Inflation (IPC) from INDEC API (monthly variation %)"""
    url = "https://apis.datos.gob.ar/series/api/series?ids=148.3_INIVELNAL_DICI_M_0_0_26"
    res = requests.get(url).json()
    last_value = res["data"][-1][1]  # last entry value
    insert_indicator("Inflacion_IPC", last_value, url)

def scrape_reserves():
    """International reserves from BCRA API (USD million)"""
    url = "https://api.estadisticasbcra.com/reservas"
    token = "YOUR_BCRA_TOKEN"  # You must request free token at estadisticasbcra.com
    headers = {"Authorization": f"BEARER {token}"}
    res = requests.get(url, headers=headers).json()
    last_value = res[-1]["valor"]
    insert_indicator("Reservas_BCRA", last_value, url)

def scrape_unemployment():
    """Unemployment rate from INDEC (quarterly %)"""
    url = "https://apis.datos.gob.ar/series/api/series?ids=143.3_UTPRUNEMP_TNA_0_0_22"
    res = requests.get(url).json()
    last_value = res["data"][-1][1]
    insert_indicator("Desempleo", last_value, url)

# ---------------- Runner ----------------

if __name__ == "__main__":
    init_db()
    scrape_dollar()
    scrape_inflation()
    try:
        scrape_reserves()
    except Exception as e:
        print("⚠️ Could not scrape reserves (need valid BCRA token).", e)
    scrape_unemployment()
    print("✅ Scraping done.")
