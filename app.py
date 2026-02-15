import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import requests
import base64
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística ITA V148", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [aria-selected="true"] { background-color: #25D366; color: white; }
    .wa-card { background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #25D366; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DEL BOT ---
st.sidebar.header("🤖 Configuración del Bot Web")
URL_BOT_WEB = st.sidebar.text_input("URL de tu Replit:", placeholder="https://tu-proyecto.replit.app")
LLAVE_ADMIN = st.sidebar.text_input("Contraseña:", value="itasecreto", type="password")
INSTANCIA = "ita_principal"

# --- FUNCIONES DEL BOT ---
def obtener_qr_web():
    headers = {"apikey": LLAVE_ADMIN, "Content-Type": "application/json"}
    try:
        requests.post(f"{URL_BOT_WEB}/instance/create", headers=headers, json={"instanceName": INSTANCIA})
        res = requests.get(f"{URL_BOT_WEB}/instance/connect/{INSTANCIA}", headers=headers)
        return res.json()
    except: return None

def enviar_pdf_web(numero, pdf_bytes, nombre_archivo, mensaje):
    headers = {"apikey": LLAVE_ADMIN, "Content-Type": "application/json"}
    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    payload = {
        "number": numero, "mediatype": "document", "mimetype": "application/pdf",
        "caption": mensaje, "media": pdf_b64, "fileName": nombre_archivo
    }
    try:
        res = requests.post(f"{URL_BOT_WEB}/message/sendMedia/{INSTANCIA}", headers=headers, json=payload)
        return res.status_code in [200, 201]
    except: return False

# --- LÓGICA DE ORDENAMIENTO (FIX: UNHASHABLE LIST) ---
def natural_sort_key(txt):
    if not txt: return tuple()
    txt = str(txt).upper()
    # USAMOS TUPLA () EN VEZ DE LISTA [] PARA EVITAR EL ERROR DE LA FRANJA ROJA
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def normalizar_numero(txt):
    nums = re.sub(r'\D', '', str(txt))
    if not nums.startswith('57') and len(nums) == 10: nums = '57' + nums
    return nums

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, sep=None, engine='python')
        for _, row in df.iterrows():
            b = str(row.iloc[0]).upper().strip()
            t = str(row.iloc[1]).upper().strip()
            c = normalizar_numero(str(row.iloc[2])) if len(row) > 2 else ""
            mapa[b] = {'nombre': t, 'celular': c}
    except: pass
    return mapa

# --- GENERADOR DE PLANILLA PDF ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102); self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.set_xy(10, 5); self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C'); self.ln(10)

def crear_pdf_lista(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page(); pdf.set_font('Arial', 'B', 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION']
    widths = [10, 30, 30, 75, 120]
    pdf.set_fill_color(220, 220, 220); pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln(); pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        def gv(k): return str(row[col_map[k]]) if k in col_map and col_map[k] in row else ""
        data = [str(idx), gv('CUENTA'), gv('MEDIDOR')[:15], str(row[col_map['BARRIO']])[:35], gv('DIRECCION')[:60]]
        for val, w in zip(data, widths):
            try: v_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: v_enc = val
            pdf.cell(w, 7, v_enc, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None

t_op, t_bot, t_cfg = st.tabs(["🚀 Procesar y Enviar", "🤖 Vincular WhatsApp", "⚙️ Maestro"])

with t_cfg:
    f_maestro = st.file_uploader("Subir Maestro (Barrio, Tecnico, Celular)")
    if f_maestro:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
        st.success("✅ Maestro cargado.")

with t_bot:
    if not URL_BOT_WEB: st.warning("Ingresa el link de Replit en la barra lateral.")
    elif st.button("🔄 Generar Código QR"):
        res = obtener_qr_web()
        if res and "base64" in str(res):
            img_data = res['base64'].split(',')[1]
            st.image(base64.b64decode(img_data), width=350)
        else: st.error("❌ Sin conexión al servidor bot.")

with t_op:
    c1, c2 = st.columns(2)
    with c1: f_pdf = st.file_uploader("PDF Pólizas", type="pdf")
    with c2: f_excel = st.file_uploader("Excel Ruta", type=["xlsx"])

    if f_excel and st.session_state['mapa_actual']:
        df_raw = pd.read_excel(f_excel)
        cols = list(df_raw.columns)
        st.divider()
        
        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            sel_cta = st.selectbox("CUENTA:", cols, index=0)
            sel_bar = st.selectbox("BARRIO:", cols, index=1)
        with cm2:
            sel_dir = st.selectbox("DIRECCIÓN:", cols, index=2)
            sel_med = st.selectbox("MEDIDOR:", ["NO TIENE"] + cols, index=0)
        with cm3:
            st.write("Cupo: 35 por técnico")

        if st.button("🚀 BALANCEAR RUTA BLINDADA", type="primary"):
            df = df_raw.copy()
            maestro = st.session_state['mapa_actual']
            df['TECNICO'] = df[sel_bar].apply(lambda x: maestro.get(str(x).upper().strip(), {}).get('nombre', 'SIN_ASIGNAR'))
            df['CELULAR'] = df[sel_bar].apply(get_cel)
            
            # ORDENAMIENTO BLINDADO (Usando tuplas para evitar el error)
            df['SORT_D'] = df[sel_dir].astype(str).apply(natural_sort_key)
            df = df.sort_values(by=[sel_bar, 'SORT_D'])
            
            st.session_state['df_simulado'] = df.drop(columns=['SORT_D'])
            st.session_state['col_map'] = {'CUENTA': sel_cta, 'BARRIO': sel_bar, 'DIRECCION': sel_dir, 'MEDIDOR': sel_med}
            st.success("✅ Ruta organizada.")

        if st.session_state['df_simulado'] is not None:
            st.divider()
            df = st.session_state['df_simulado']
            for tec in sorted(df['TECNICO'].unique()):
                if tec == "SIN_ASIGNAR": continue
                sub = df[df['TECNICO'] == tec]
                cel = sub['CELULAR'].iloc[0]
                with st.container():
                    st.markdown(f"""<div class="wa-card"><b>👷 {tec}</b> - {len(sub)} gestiones</div>""", unsafe_allow_html=True)
                    if st.button(f"🤖 Mandar Hoja de Ruta a {tec}", key=f"btn_{tec}"):
                        pdf_bytes = crear_pdf_lista(sub, tec, st.session_state['col_map'])
                        msg = f"Hola {tec}, te envío tu ruta de hoy. ¡Dale con toda!"
                        if enviar_pdf_web(cel, pdf_bytes, f"Ruta_{tec}.pdf", msg):
                            st.success(f"¡Enviado!")
                        else: st.error("Error al enviar.")
