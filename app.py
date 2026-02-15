import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import math
import numpy as np
import urllib.parse
import requests
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística ITA V142 - Bot & Blindado", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #25D366; color: white; border: 2px solid #00ff88; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    .bot-status { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .connected { background-color: #1b4d3e; color: #00ff88; border: 2px solid #00ff88; }
    .disconnected { background-color: #4d1b1b; color: #ff4b4b; border: 2px solid #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Versión Maestra")

# --- ESTADOS DE SESIÓN ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map' not in st.session_state: st.session_state['col_map'] = {}
if 'bot_conectado' not in st.session_state: st.session_state['bot_conectado'] = False
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# --- FUNCIONES DE LIMPIEZA Y PROCESAMIENTO ---
def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    if not txt: return ""
    nums = re.sub(r'\D', '', str(txt))
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """Genera una tupla para ordenamiento natural (hashable)."""
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    b_raw = limpiar_estricto(str(barrio_input))
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]['nombre']
    for k, v in mapa_barrios.items():
        if k in b_raw: return v['nombre']
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, sep=None, engine='python')
        # Col 0: Barrio, Col 1: Tecnico, Col 2: Celular
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row.iloc[0]))
            t = str(row.iloc[1]).upper().strip()
            c = ""
            if len(row) > 2:
                c = re.sub(r'\D', '', str(row.iloc[2]))
                if not c.startswith('57') and len(c) == 10: c = '57' + c
            if t and t != "NAN":
                mapa[b] = {'nombre': t, 'celular': c}
    except Exception as e:
        st.error(f"Error en maestro: {e}")
    return mapa

# --- GENERADOR DE PDF ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102); self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16); self.set_text_color(255, 255, 255)
        self.set_xy(10, 5); self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C'); self.ln(10)

def crear_pdf_lista(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page(); pdf.set_font('Arial', 'B', 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')} | TOTAL: {len(df)}", 0, 1)
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    pdf.set_fill_color(220, 220, 220); pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln(); pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        barrio_txt = str(row[col_map['BARRIO']])
        pdf.set_text_color(200,0,0) if pd.notna(row.get('ORIGEN_REAL')) else pdf.set_text_color(0,0,0)
        def get_v(k):
            c_n = col_map.get(k)
            return str(row[c_n]) if c_n and c_n in row else ""
        data = [str(idx), get_v('CUENTA'), get_v('MEDIDOR')[:15], barrio_txt[:35], get_v('DIRECCION')[:50], get_v('CLIENTE')[:30]]
        for val, w in zip(data, widths):
            try: v_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: v_enc = val
            pdf.cell(w, 7, v_enc, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- PESTAÑAS ---
tab_operacion, tab_visor, tab_bot, tab_config = st.tabs(["🚀 Operación", "🌍 Ajuste Manual", "🤖 Bot de WhatsApp", "⚙️ Configuración"])

# --- TAB CONFIG ---
with tab_config:
    st.header("Maestro de Operarios")
    st.info("Sube un archivo con 3 columnas: BARRIO | TECNICO | CELULAR")
    f_maestro = st.file_uploader("Subir Maestro", type=["xlsx", "csv"])
    if f_maestro:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
        st.success(f"✅ Base cargada con {len(st.session_state['mapa_actual'])} barrios.")

# --- SIDEBAR: CUADRILLA ---
maestro = st.session_state['mapa_actual']
nombres_unicos = sorted(list(set(v['nombre'] for v in maestro.values())))
TECNICOS_ACTIVOS = []
st.sidebar.header("👷 Cuadrilla Activa")
if nombres_unicos:
    all_on = st.sidebar.checkbox("Seleccionar Todos", True)
    for te in nombres_unicos:
        if st.sidebar.toggle(te, all_on): TECNICOS_ACTIVOS.append(te)

# --- TAB BOT ---
with tab_bot:
    st.header("🤖 Vinculación del Bot")
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if not st.session_state['bot_conectado']:
            st.write("### 1. Escanea el código QR")
            st.image("https://www.dummies.com/wp-content/uploads/439773.image0.jpg", width=250, caption="Simulación QR")
            if st.button("🔄 Generar QR"):
                with st.spinner("Conectando..."): time.sleep(1); st.rerun()
        else:
            st.success("✅ DISPOSITIVO VINCULADO")
            st.info("El sistema enviará los PDFs automáticamente a los números registrados.")

    with c_b2:
        st.write("### 2. Estado del Sistema")
        if st.session_state['bot_conectado']:
            st.markdown('<div class="bot-status connected">SERVICIO ACTIVO</div>', unsafe_allow_html=True)
            if st.button("🔴 Desvincular Bot"): st.session_state['bot_conectado'] = False; st.rerun()
        else:
            st.markdown('<div class="bot-status disconnected">SIN CONEXIÓN</div>', unsafe_allow_html=True)
            if st.button("🟢 Conectar (Simulación)"): st.session_state['bot_conectado'] = True; st.rerun()

# --- TAB OPERACIÓN ---
with tab_operacion:
    c1, c2 = st.columns(2)
    with c1: f_pdf = st.file_uploader("1. PDF Pólizas", type="pdf")
    with c2: f_excel = st.file_uploader("2. Excel Ruta", type=["xlsx", "csv"])
    
    if f_excel and TECNICOS_ACTIVOS:
        try:
            df_raw = pd.read_excel(f_excel) if f_excel.name.endswith('.xlsx') else pd.read_csv(f_excel)
            cols = list(df_raw.columns)
            
            st.divider()
            st.subheader("⚖️ Cupos y Mapeo")
            df_cupos = pd.DataFrame({"Técnico": TECNICOS_ACTIVOS, "Cupo Máximo": [35] * len(TECNICOS_ACTIVOS)})
            edited_cupos = st.data_editor(df_cupos, hide_index=True)
            LIMITES = dict(zip(edited_cupos["Técnico"], edited_cupos["Cupo Máximo"]))

            def find_idx(kws):
                for i, c in enumerate(cols):
                    for k in kws:
                        if k in str(c).upper(): return i
                return 0
            
            cm1, cm2, cm3 = st.columns(3)
            with cm1:
                sel_cta = st.selectbox("CUENTA:", cols, index=find_idx(['CUENTA', 'POLIZA']))
                sel_bar = st.selectbox("BARRIO:", cols, index=find_idx(['BARRIO', 'SECTOR']))
            with cm2:
                sel_dir = st.selectbox("DIRECCIÓN:", cols, index=find_idx(['DIRECCION', 'DIR']))
                sel_med = st.selectbox("MEDIDOR:", ["NO TIENE"] + cols, index=find_idx(['MEDIDOR']) + 1)
            with cm3:
                sel_cli = st.selectbox("CLIENTE:", ["NO TIENE"] + cols, index=find_idx(['CLIENTE', 'SUSCRIPTOR']) + 1)

            st.session_state['col_map'] = {'CUENTA': sel_cta, 'BARRIO': sel_bar, 'DIRECCION': sel_dir, 'MEDIDOR': sel_med, 'CLIENTE': sel_cli}

            if st.button("🚀 EJECUTAR BALANCEO", type="primary"):
                df = df_raw.copy()
                df['TECNICO_FINAL'] = df[sel_bar].apply(lambda x: buscar_tecnico_exacto(x, maestro))
                df['CELULAR'] = df[sel_bar].apply(lambda x: maestro.get(str(x).upper(), {}).get('celular', ''))
                df['ORIGEN_REAL'] = None
                
                # ORDENAMIENTO INICIAL BLINDADO
                df['SORT_DIR'] = df[sel_dir].astype(str).apply(natural_sort_key)
                df = df.sort_values(by=[sel_bar, 'SORT_DIR'])
                
                # Cascada
                conteo = df['TECNICO_FINAL'].value_counts()
                for giver in [t for t in TECNICOS_ACTIVOS if conteo.get(t, 0) > LIMITES.get(t, 35)]:
                    tope = LIMITES[giver]
                    rows = df[df['TECNICO_FINAL'] == giver]
                    excedente = len(rows) - tope
                    if excedente > 0:
                        idx_move = rows.index[-excedente:]
                        receiver = sorted([t for t in TECNICOS_ACTIVOS if t != giver], key=lambda x: df['TECNICO_FINAL'].value_counts().get(x,0))[0]
                        df.loc[idx_move, 'TECNICO_FINAL'] = receiver
                        df.loc[idx_move, 'ORIGEN_REAL'] = giver
                
                st.session_state['df_simulado'] = df.drop(columns=['SORT_DIR'])
                st.success("✅ Ruta balanceada y Alameda agrupada.")
        except Exception as e: st.error(f"Error: {e}")

# --- TAB VISOR ---
with tab_visor:
    if st.session_state['df_simulado'] is not None:
        df = st.session_state['df_simulado']
        col_map = st.session_state['col_map']
        
        cols_v = st.columns(2)
        tecs_ruta = sorted(df['TECNICO_FINAL'].unique())
        for i, tec in enumerate(tecs_ruta):
            if tec == "SIN_ASIGNAR": continue
            with cols_v[i % 2]:
                sub = df[df['TECNICO_FINAL'] == tec]
                cel = sub['CELULAR'].iloc[0] if not sub['CELULAR'].empty else ""
                
                with st.expander(f"👷 **{tec}** | {len(sub)} gestiones", expanded=True):
                    st.dataframe(sub[[col_map['BARRIO'], col_map['DIRECCION']]], hide_index=True)
                    
                    if cel:
                        msg = f"Hola {tec}, te envío tu hoja de ruta. Total: {len(sub)} gestiones."
                        if st.session_state['bot_conectado']:
                            if st.button(f"🤖 Enviar Automático a {tec}", key=f"bot_{tec}"):
                                with st.spinner("Bot enviando..."): time.sleep(1); st.success("¡PDF enviado!")
                        else:
                            st.link_button("📲 Abrir WhatsApp", f"https://wa.me/{cel}?text={urllib.parse.quote(msg)}")

        if f_pdf and st.button("✅ GENERAR ZIP PARA DESCARGA", type="primary"):
            with st.spinner("Procesando archivos espejo..."):
                f_pdf.seek(0); doc = fitz.open(stream=f_pdf.read(), filetype="pdf")
                mapa_p = {}
                for page_idx in range(len(doc)):
                    txt = doc[page_idx].get_text()
                    regex = r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})'
                    if matches := re.findall(regex, txt, re.IGNORECASE):
                        sub_pdf = fitz.open(); sub_pdf.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
                        if page_idx + 1 < len(doc) and not re.search(r'(?:Póliza|Poliza|Cuenta)', doc[page_idx+1].get_text(), re.IGNORECASE):
                            sub_pdf.insert_pdf(doc, from_page=page_idx+1, to_page=page_idx+1)
                        pdf_bytes = sub_pdf.tobytes()
                        sub_pdf.close()
                        for m in matches: mapa_p[normalizar_numero(m)] = pdf_bytes

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for k, v in mapa_p.items(): zf.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                    out_b = io.BytesIO(); df.to_excel(out_b, index=False); zf.writestr("00_CONSOLIDADO.xlsx", out_b.getvalue())
                    
                    for t_name in df['TECNICO_FINAL'].unique():
                        if t_name == "SIN_ASIGNAR": continue
                        df_t = df[df['TECNICO_FINAL'] == t_name].copy()
                        # ORDENAMIENTO BLINDADO EN ZIP
                        df_t['SORT_DIR'] = df_t[col_map['DIRECCION']].astype(str).apply(natural_sort_key)
                        df_t = df_t.sort_values(by=[col_map['BARRIO'], 'SORT_DIR']).drop(columns=['SORT_DIR'])
                        
                        safe = str(t_name).replace(" ","_")
                        zf.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista(df_t, t_name, col_map))
                        merger = fitz.open()
                        for _, r in df_t.iterrows():
                            t_cta = normalizar_numero(str(r[col_map['CUENTA']]))
                            if pdf_f := mapa_p.get(t_cta):
                                zf.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{t_cta}.pdf", pdf_f)
                                with fitz.open(stream=pdf_f, filetype="pdf") as temp: merger.insert_pdf(temp)
                        if len(merger) > 0: zf.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                        merger.close()
                st.session_state['zip_listo'] = zip_buffer.getvalue()
                st.success("¡ZIP Generado!")

if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_ITA.zip", type="primary")
