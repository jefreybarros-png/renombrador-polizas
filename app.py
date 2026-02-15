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

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Implacable V129", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; }
    .success { background-color: #1b4d3e; color: #ccffdd; }
    .warning { background-color: #7d5e00; color: #fff4cc; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Sincronización y Rastreo Total")

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """Quita ceros a la izquierda y espacios para comparar números."""
    if not txt: return ""
    # Dejar solo dígitos
    nums = re.sub(r'\D', '', str(txt))
    if nums:
        return str(int(nums)) # Esto convierte "00123" en "123"
    return ""

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(barrio_input)
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    b_flex = re.sub(r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA)\b', '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    for k, v in mapa_barrios.items():
        if k in b_raw: return v
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        c_b, c_t = df.columns[0], df.columns[1]
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_b]))
            t = str(row[c_t]).upper().strip()
            if t and t != "NAN": mapa[b] = t
    except: pass
    return mapa

def calcular_peso_js(txt):
    clean = limpiar_estricto(txt)
    penalidad = 5000 if "SUR" in clean else 0
    nums = re.findall(r'(\d+)', clean)
    ref = int(nums[0]) if nums else 0
    if "CL" in clean or "CALLE" in clean: peso = (110 - ref) * 1000
    else: peso = ref * 1000
    return peso + penalidad + (int(nums[1]) if len(nums)>1 else 0)

# PDF LISTADO
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')} | TOTAL: {len(df)}", 0, 1)
    
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        barrio_txt = str(row[col_map['BARRIO']])
        if pd.notna(row.get('ORIGEN_REAL')):
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)

        data_row = [
            str(idx),
            str(row[col_map['CUENTA']]),
            str(row[col_map['MEDIDOR']])[:15] if col_map['MEDIDOR'] else "",
            barrio_txt[:35],
            str(row[col_map['DIRECCION']])[:50] if col_map['DIRECCION'] else "",
            str(row[col_map['CLIENTE']])[:30] if col_map['CLIENTE'] else ""
        ]
        for val, w in zip(data_row, widths):
            try: val_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_enc = val
            pdf.cell(w, 7, val_enc, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- SESSION ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# --- UI TABS ---
tab_operacion, tab_visor, tab_config = st.tabs(["🚀 Carga", "🌍 Visor Manual", "⚙️ Operarios"])

# --- TAB 3: CONFIG ---
with tab_config:
    st.header("Base de Operarios")
    maestro_file = st.file_uploader("Subir Maestro", type=["xlsx", "csv"])
    if maestro_file:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
        st.success("✅ Actualizado")

# --- SIDEBAR ---
lista_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
TECNICOS_ACTIVOS = []
st.sidebar.header("👷 Cuadrilla")
if lista_tecnicos:
    all_on = st.sidebar.checkbox("Seleccionar Todos", value=True)
    for tec in lista_tecnicos:
        if st.sidebar.toggle(f"{tec}", value=all_on): TECNICOS_ACTIVOS.append(tec)

# --- TAB 1: CARGA ---
with tab_operacion:
    c1, c2 = st.columns(2)
    with c1: pdf_in = st.file_uploader("1. PDF Pólizas", type="pdf")
    with c2: excel_in = st.file_uploader("2. Excel Ruta", type=["xlsx", "csv"])
    
    if excel_in and lista_tecnicos:
        if st.button("🚀 INICIAR BALANCEO", type="primary"):
            try:
                if excel_in.name.endswith('.csv'): df = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(excel_in)
                df.columns = [limpiar_estricto(c) for c in df.columns]
                
                def find(k_list):
                    for k in k_list:
                        for c in df.columns: 
                            if x := re.search(k, c, re.IGNORECASE): return c # Regex search mas flexible
                            if k in c: return c
                    return None
                
                c_barrio = find(r'BARRIO|SECTOR|URB')
                c_cta = find(r'CUENTA|POLIZA|CONTRATO|SUSCRIP') # Regex
                
                if c_barrio and c_cta:
                    df['TECNICO_IDEAL'] = df[c_barrio].apply(lambda x: buscar_tecnico_exacto(str(x), st.session_state['mapa_actual']))
                    df['TECNICO_FINAL'] = df['TECNICO_IDEAL']
                    df['ORIGEN_REAL'] = None
                    
                    # Balanceo Cascada
                    TOPE = math.ceil(len(df)/len(TECNICOS_ACTIVOS)) if TECNICOS_ACTIVOS else 35
                    conteo = df['TECNICO_IDEAL'].value_counts()
                    overs = [t for t in TECNICOS_ACTIVOS if conteo.get(t, 0) > TOPE]
                    
                    for giver in overs:
                        rows = df[df['TECNICO_FINAL'] == giver]
                        excedente = len(rows) - TOPE
                        if excedente > 0:
                            idx_move = rows.index[-excedente:]
                            counts_now = df['TECNICO_FINAL'].value_counts()
                            candidates = [t for t in TECNICOS_ACTIVOS if t != giver and counts_now.get(t, 0) < TOPE]
                            if candidates:
                                receiver = sorted(candidates, key=lambda x: counts_now.get(x, 0))[0]
                                df.loc[idx_move, 'TECNICO_FINAL'] = receiver
                                df.loc[idx_move, 'ORIGEN_REAL'] = giver

                    for t in df['TECNICO_FINAL'].unique():
                        if t not in TECNICOS_ACTIVOS and t != "SIN_ASIGNAR":
                            idx_absent = df[df['TECNICO_FINAL'] == t].index
                            counts_now = df['TECNICO_FINAL'].value_counts()
                            candidates = [c for c in TECNICOS_ACTIVOS if counts_now.get(c, 0) < TOPE + 15]
                            if candidates:
                                receiver = sorted(candidates, key=lambda x: counts_now.get(x, 0))[0]
                                df.loc[idx_absent, 'TECNICO_FINAL'] = receiver
                                df.loc[idx_absent, 'ORIGEN_REAL'] = f"{t} (AUSENTE)"
                            else:
                                df.loc[idx_absent, 'TECNICO_FINAL'] = "SIN_GESTOR_ACTIVO"

                    st.session_state['df_simulado'] = df
                    st.session_state['col_barrio'] = c_barrio
                    st.session_state['col_cta'] = c_cta
                    st.session_state['col_dir'] = find(r'DIR|UBIC|DIREC')
                    st.session_state['col_med'] = find(r'MED|SERIE|APA')
                    st.session_state['col_cli'] = find(r'CLI|NOM|SUS')
                    
                    st.success("✅ Balanceo completado.")
                else: st.error("Faltan columnas BARRIO o CUENTA.")
            except Exception as e: st.error(f"Error procesando: {e}")

# --- TAB 2: VISOR ---
with tab_visor:
    if st.session_state['df_simulado'] is not None:
        df = st.session_state['df_simulado']
        c_barrio = st.session_state['col_barrio']
        
        # MOVER
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
        with c1: org = st.selectbox("Origen:", ["-"] + sorted(df['TECNICO_FINAL'].unique()))
        with c2: 
            if org != "-":
                bars = df[df['TECNICO_FINAL']==org][c_barrio].value_counts()
                bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in bars.items()])
            else: bar = None
        with c3: dest = st.selectbox("Destino:", ["-"] + TECNICOS_ACTIVOS)
        with c4: 
            st.write(""); 
            if st.button("MOVER"):
                if bar and dest != "-":
                    real_b = bar.rsplit(" (", 1)[0]
                    mask = (df['TECNICO_FINAL'] == org) & (df[c_barrio] == real_b)
                    df.loc[mask, 'TECNICO_FINAL'] = dest
                    df.loc[mask, 'ORIGEN_REAL'] = org
                    st.session_state['df_simulado'] = df
                    st.rerun()

        st.divider()
        cols = st.columns(2)
        tecnicos = sorted(df['TECNICO_FINAL'].unique())
        for i, tec in enumerate(tecnicos):
            with cols[i % 2]:
                sub = df[df['TECNICO_FINAL'] == tec]
                resumen = sub.groupby([c_barrio, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='Cant')
                resumen['Detalle'] = resumen.apply(lambda x: f"⚠️ {x[c_barrio]} (APOYO)" if pd.notna(x['ORIGEN_REAL']) else x[c_barrio], axis=1)
                with st.expander(f"👷 **{tec}** | Total: {len(sub)}", expanded=True):
                    st.dataframe(resumen[['Detalle', 'Cant']], hide_index=True, use_container_width=True)

        st.divider()
        if pdf_in:
            if st.button("✅ GENERAR PAQUETE COMPLETO (DOBLE RESPALDO)", type="primary"):
                with st.spinner("Indexando PDFs y creando carpetas..."):
                    df['CARPETA'] = df['TECNICO_FINAL']
                    
                    # 1. INDEXAR PDF (RASTREO IMPLACABLE)
                    pdf_in.seek(0)
                    doc = fitz.open(stream=pdf_in.read(), filetype="pdf")
                    # Diccionario Inverso: {Numero_Normalizado: Bytes_PDF}
                    mapa_p = {} 
                    
                    prog_bar = st.progress(0)
                    for i in range(len(doc)):
                        txt = doc[i].get_text()
                        
                        # ESTRATEGIA MULTIPUNTO: Capturar TODOS los números posibles de la hoja
                        # Esto encuentra Cuentas, Medidores y Referencias
                        matches = re.findall(r'\b(\d{4,15})\b', txt)
                        
                        # Extraer página (y posible anexo)
                        sub = fitz.open()
                        sub.insert_pdf(doc, from_page=i, to_page=i)
                        if i + 1 < len(doc):
                            txt_next = doc[i+1].get_text()
                            if "Poliza" not in txt_next and "Cuenta" not in txt_next:
                                sub.insert_pdf(doc, from_page=i+1, to_page=i+1)
                        pdf_bytes = sub.tobytes()
                        sub.close()
                        
                        # Asociar TODOS los números encontrados a esta página
                        for m in matches:
                            norm = normalizar_numero(m)
                            if norm: mapa_p[norm] = pdf_bytes
                        
                        if i % 10 == 0: prog_bar.progress(i / len(doc))
                    
                    prog_bar.progress(100)

                    # 2. GENERAR ZIP
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        # Archivos Generales
                        for k_num, p_bytes in mapa_p.items():
                            # Solo guardamos en backup general uno por número para no duplicar demasiado
                            # (Opcional: saltar esto para ahorrar espacio si son muchos)
                            pass
                        
                        # Excel Maestro
                        out_b = io.BytesIO()
                        with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                        zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", out_b.getvalue())
                        
                        c_map = {'CUENTA': st.session_state['col_cta'], 'MEDIDOR': st.session_state['col_med'], 'BARRIO': c_barrio, 'DIRECCION': st.session_state['col_dir'], 'CLIENTE': st.session_state['col_cli']}
                        
                        reporte_faltantes = []

                        for tec in df['CARPETA'].unique():
                            if "SIN_" in tec: continue
                            safe = str(tec).replace(" ","_")
                            df_t = df[df['CARPETA'] == tec].copy()
                            
                            # ORDENAMIENTO (Crucial para sincronización)
                            if st.session_state['col_dir']:
                                df_t['P'] = df_t[st.session_state['col_dir']].astype(str).apply(calcular_peso_js)
                                df_t = df_t.sort_values('P')
                            
                            # A. HOJA DE RUTA
                            pdf_h = crear_pdf_lista(df_t, tec, c_map)
                            zf.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", pdf_h)
                            
                            # B. EXCEL TÉCNICO
                            out_t = io.BytesIO()
                            with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                            zf.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", out_t.getvalue())
                            
                            # C. BUSQUEDA Y ARMADO DE PDFs
                            merger = fitz.open()
                            count_merged = 0
                            
                            for _, r in df_t.iterrows():
                                # Intentamos buscar por CUENTA y por MEDIDOR
                                targets = []
                                if st.session_state['col_cta']: targets.append(str(r[st.session_state['col_cta']]))
                                if st.session_state['col_med']: targets.append(str(r[st.session_state['col_med']]))
                                
                                pdf_found = None
                                used_key = ""
                                
                                for t in targets:
                                    tn = normalizar_numero(t)
                                    if tn in mapa_p:
                                        pdf_found = mapa_p[tn]
                                        used_key = tn
                                        break
                                
                                if pdf_found:
                                    # 1. Guardar en carpeta individual (Lo que pediste "de adentro")
                                    zf.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{used_key}.pdf", pdf_found)
                                    
                                    # 2. Pegar al unificado
                                    with fitz.open(stream=pdf_found, filetype="pdf") as temp:
                                        merger.insert_pdf(temp)
                                    count_merged += 1
                                else:
                                    reporte_faltantes.append(f"{tec} -> {targets[0]}")

                            if count_merged > 0:
                                zf.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                            merger.close()
                        
                        if reporte_faltantes:
                            zf.writestr("REPORTE_FALTANTES.txt", "\n".join(reporte_faltantes))

                    st.session_state['zip_listo'] = zip_buffer.getvalue()
                    
                    if reporte_faltantes:
                        st.warning(f"⚠️ Proceso terminado. Faltaron {len(reporte_faltantes)} pólizas (ver REPORTE_FALTANTES.txt).")
                    else:
                        st.success("✅ ¡Perfecto! Todos los archivos generados y sincronizados.")
    else:
        st.info("Sube archivos.")

if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_Total.zip", "application/zip", type="primary")
