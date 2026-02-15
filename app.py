import streamlit as st
import fitz
import pandas as pd
import re
import io
import zipfile
from fpdf import FPDF
from datetime import datetime
import requests
import base64
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística ITA V148", layout="wide")
st.markdown("<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>", unsafe_allow_html=True)

# --- BOTONES DEL SIDEBAR ---
st.sidebar.header("🤖 Configuración del Bot")
URL_REPLIT = st.sidebar.text_input("URL de tu Replit:", value="https://evolution-api--jefreybarros.replit.app")
LLAVE_API = st.sidebar.text_input("Contraseña (API KEY):", value="itasecreto", type="password")

# --- FUNCIONES DEL BOT ---
def conectar_bot():
    headers = {"apikey": LLAVE_API, "Content-Type": "application/json"}
    try:
        requests.post(f"{URL_REPLIT}/instance/create", headers=headers, json={"instanceName": "ita_principal"})
        res = requests.get(f"{URL_REPLIT}/instance/connect/ita_principal", headers=headers)
        return res.json()
    except: return None

# --- FIX DEL ERROR ROJO (NATURAL SORT) ---
def natural_sort_key(txt):
    if not txt: return tuple()
    # CAMBIO CLAVE: Usamos tuple() para evitar el error 'unhashable list'
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', str(txt).upper()))

# --- (Resto de funciones de carga e interfaz...) ---
st.title("🎯 Logística ITA: Versión Blindada")
t_op, t_bot, t_cfg = st.tabs(["🚀 Procesar Ruta", "🤖 Vincular WhatsApp", "⚙️ Maestro"])

with t_bot:
    if st.button("🔄 Generar Código QR"):
        res = conectar_bot()
        if res and "base64" in str(res):
            st.image(base64.b64decode(res['base64'].split(',')[1]), width=350)
        else: st.error("Sin conexión al servidor bot. Verifica el link y la clave.")

with t_op:
    f_excel = st.file_uploader("Excel Ruta", type=["xlsx"])
    if f_excel:
        df = pd.read_excel(f_excel)
        c_dir = next(c for c in df.columns if 'DIR' in str(c).upper())
        if st.button("🚀 BALANCEAR RUTA"):
            # Aquí se aplica el ordenamiento corregido
            df['SORT_D'] = df[c_dir].astype(str).apply(natural_sort_key)
            df = df.sort_values(by=[df.columns[1], 'SORT_D'])
            st.session_state['df_simulado'] = df
            st.success("✅ Ruta organizada sin errores.")
