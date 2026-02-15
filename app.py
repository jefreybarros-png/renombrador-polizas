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
st.set_page_config(page_title="Logística Ordenada V136", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Ordenamiento por Barrio Estricto")

# --- FUNCIONES DE LIMPIEZA Y ORDEN ---
def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    if not txt: return ""
    nums = re.sub(r'\D', '', str(txt))
    return str(int(nums)) if nums else ""

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(str(barrio_input))
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

# --- REEMPLAZA ESTA FUNCIÓN ---
def natural_sort_key(txt):
    if not txt: return tuple()
    txt = str(txt).upper()
    # Cambiamos los corchetes [] por tuple() para que sea "hashable"
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# --- Y EN EL MOMENTO DE GENERAR EL ZIP, ASEGÚRATE DE ESTO ---
# Dentro del bloque de generación del ZIP, donde ordenamos por barrio:

for tec in df['CARPETA'].unique():
    if "SIN_" in tec: continue
    safe = str(tec).replace(" ","_")
    df_t = df[df['CARPETA'] == tec].copy()
    
    # ORDENAMIENTO BLOQUEADO POR BARRIO
    c_dir = col_map.get('DIRECCION')
    if c_dir:
        # Aquí aplicamos la función que ahora devuelve una TUPLA
        df_t['SORT_DIR'] = df_t[c_dir].astype(str).apply(natural_sort_key)
        
        # Ordenamos por Barrio y luego por la tupla de dirección
        df_t = df_t.sort_values(by=[col_map['BARRIO'], 'SORT_DIR'])
        
        # Borramos la columna temporal para que no salga en el Excel final
        df_t = df_t.drop(columns=['SORT_DIR'])

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

        def get_val(key):
            col_name = col_map.get(key)
            if col_name and col_name != "NO TIENE":
                return str(row[col_name])
            return ""

        data_row = [
            str(idx),
            get_val('CUENTA'),
            get_val('MEDIDOR')[:15],
            barrio_txt[:35],
            get_val('DIRECCION')[:50],
            get_val('CLIENTE')[:30]
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
if 'col_map' not in st.session_state: st.session_state['col_map'] = {}

# --- TABS ---
tab_operacion, tab_visor, tab_config = st.tabs(["🚀 Carga y Cupos", "🌍 Visor Manual", "⚙️ Operarios"])

# --- TAB 3: CONFIG ---
with tab_config:
    st.header("Base de Operarios")
    maestro_file = st.file_uploader("Subir Maestro (Barrio | Técnico)", type=["xlsx", "csv"])
    if maestro_file:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
        st.success("✅ Base Actualizada")

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
        try:
            if excel_in.name.endswith('.csv'): df_raw = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
            else: df_raw = pd.read_excel(excel_in)
            cols_excel = list(df_raw.columns)
            
            # CUPOS
            st.divider()
            st.subheader("⚖️ Cupos Individuales")
            df_topes_init = pd.DataFrame({"Técnico": TECNICOS_ACTIVOS, "Cupo Máximo": [35] * len(TECNICOS_ACTIVOS)})
            edited_topes = st.data_editor(df_topes_init, column_config={"Cupo Máximo": st.column_config.NumberColumn(min_value=1, max_value=200, step=1)}, hide_index=True, use_container_width=True)
            LIMITES_INDIVIDUALES = dict(zip(edited_topes["Técnico"], edited_topes["Cupo Máximo"]))

            # MAPEO
            st.divider()
            st.subheader("🔗 Mapeo de Columnas")
            def idx_of(keywords):
                for i, col in enumerate(cols_excel):
                    for k in keywords:
                        if k in str(col).upper(): return i
                return 0

            cm1, cm2, cm3 = st.columns(3)
            with cm1:
                sel_cta = st.selectbox("CUENTA/PÓLIZA:", cols_excel, index=idx_of(['CUENTA', 'POLIZA']))
                sel_bar = st.selectbox("BARRIO:", cols_excel, index=idx_of(['BARRIO', 'SECTOR']))
            with cm2:
                sel_dir = st.selectbox("DIRECCIÓN:", cols_excel, index=idx_of(['DIRECCION', 'DIR']))
                sel_med = st.selectbox("MEDIDOR:", ["NO TIENE"] + cols_excel, index=idx_of(['MEDIDOR', 'SERIE']) + 1)
            with cm3:
                sel_cli = st.selectbox("CLIENTE:", ["NO TIENE"] + cols_excel, index=idx_of(['CLIENTE', 'NOMBRE']) + 1)

            st.session_state['col_map'] = {
                'CUENTA': sel_cta, 'BARRIO': sel_bar, 'DIRECCION': sel_dir,
                'MEDIDOR': sel_med if sel_med != "NO TIENE" else None,
                'CLIENTE': sel_cli if sel_cli != "NO TIENE" else None
            }

            if st.button("🚀 APLICAR CUPOS Y BALANCEAR", type="primary"):
                df = df_raw.copy()
                df['TECNICO_IDEAL'] = df[sel_bar].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                df['TECNICO_FINAL'] = df['TECNICO_IDEAL']
                df['ORIGEN_REAL'] = None
                
                # --- ORDENAMIENTO CRUCIAL (BARRIO PRIMERO, LUEGO DIRECCIÓN) ---
                if sel_dir:
                    df['SORT_DIR'] = df[sel_dir].astype(str).apply(natural_sort_key)
                    # Forzamos que se agrupe por Barrio primero para que Alameda no "salte"
                    df = df.sort_values(by=[sel_bar, 'SORT_DIR'])
                
                # BALANCEO ESTRICTO
                conteo_inicial = df['TECNICO_IDEAL'].value_counts()
                overs = [t for t in TECNICOS_ACTIVOS if conteo_inicial.get(t, 0) > LIMITES_INDIVIDUALES.get(t, 35)]
                
                for giver in overs:
                    tope = LIMITES_INDIVIDUALES.get(giver, 35)
                    rows = df[df['TECNICO_FINAL'] == giver]
                    excedente = len(rows) - tope
                    if excedente > 0:
                        idx_move = rows.index[-excedente:]
                        counts_now = df['TECNICO_FINAL'].value_counts()
                        best_cand = None
                        max_space = -1
                        for cand in TECNICOS_ACTIVOS:
                            if cand == giver: continue
                            carga_cand = counts_now.get(cand, 0)
                            tope_cand = LIMITES_INDIVIDUALES.get(cand, 35)
                            espacio = tope_cand - carga_cand
                            if espacio > 0 and espacio > max_space:
                                max_space = espacio; best_cand = cand
                        if not best_cand: best_cand = sorted(TECNICOS_ACTIVOS, key=lambda x: counts_now.get(x, 0))[0]
                        df.loc[idx_move, 'TECNICO_FINAL'] = best_cand
                        df.loc[idx_move, 'ORIGEN_REAL'] = giver

                # Manejo de Ausentes
                for t in df['TECNICO_FINAL'].unique():
                    if t not in TECNICOS_ACTIVOS and t != "SIN_ASIGNAR":
                        idx_abs = df[df['TECNICO_FINAL'] == t].index
                        best_cand = sorted(TECNICOS_ACTIVOS, key=lambda x: df['TECNICO_FINAL'].value_counts().get(x, 0))[0]
                        df.loc[idx_abs, 'TECNICO_FINAL'] = best_cand
                        df.loc[idx_abs, 'ORIGEN_REAL'] = f"{t} (AUSENTE)"

                st.session_state['df_simulado'] = df
                st.success("✅ Asignación completada.")

        except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: VISOR ---
with tab_visor:
    if st.session_state['df_simulado'] is not None:
        df = st.session_state['df_simulado']
        col_map = st.session_state['col_map']
        c_barrio = col_map['BARRIO']
        
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
            if st.button("✅ GENERAR PAQUETE ESTRUCTURADO", type="primary"):
                with st.spinner("Procesando PDFs..."):
                    df['CARPETA'] = df['TECNICO_FINAL']
                    pdf_in.seek(0)
                    doc = fitz.open(stream=pdf_in.read(), filetype="pdf")
                    mapa_p = {} 
                    
                    for i in range(len(doc)):
                        txt = doc[i].get_text()
                        regex_flex = r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})'
                        matches = re.findall(regex_flex, txt, re.IGNORECASE)
                        sub = fitz.open()
                        sub.insert_pdf(doc, from_page=i, to_page=i)
                        if i + 1 < len(doc):
                            txt_next = doc[i+1].get_text()
                            if not re.search(r'(?:Póliza|Poliza|Cuenta)', txt_next, re.IGNORECASE):
                                sub.insert_pdf(doc, from_page=i+1, to_page=i+1)
                        pdf_bytes = sub.tobytes()
                        sub.close()
                        for m in matches:
                            norm = normalizar_numero(m)
                            if norm: mapa_p[norm] = pdf_bytes

                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for k_num, p_bytes in mapa_p.items():
                            if len(k_num) > 4: zf.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k_num}.pdf", p_bytes)
                        out_b = io.BytesIO()
                        with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                        zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", out_b.getvalue())
                        
                        for tec in df['CARPETA'].unique():
                            if "SIN_" in tec: continue
                            safe = str(tec).replace(" ","_")
                            df_t = df[df['CARPETA'] == tec].copy()
                            
                            # --- ORDENAMIENTO FINAL BLOQUEADO POR BARRIO ---
                            if col_map.get('DIRECCION'):
                                df_t['SORT_DIR'] = df_t[col_map['DIRECCION']].astype(str).apply(natural_sort_key)
                                # AQUÍ ESTÁ LA SOLUCIÓN: Ordenamos Barrio + Direccion
                                df_t = df_t.sort_values(by=[col_map['BARRIO'], 'SORT_DIR'])
                            
                            pdf_h = crear_pdf_lista(df_t, tec, col_map)
                            zf.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", pdf_h)
                            out_t = io.BytesIO()
                            with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                            zf.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", out_t.getvalue())
                            
                            merger = fitz.open()
                            count_merged = 0
                            for _, r in df_t.iterrows():
                                t_cuenta = normalizar_numero(str(r[col_map['CUENTA']]))
                                pdf_found = mapa_p.get(t_cuenta)
                                if pdf_found:
                                    zf.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{t_cuenta}.pdf", pdf_found)
                                    with fitz.open(stream=pdf_found, filetype="pdf") as temp: merger.insert_pdf(temp)
                                    count_merged += 1
                            if count_merged > 0: zf.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                            merger.close()

                    st.session_state['zip_listo'] = zip_buffer.getvalue()
                    st.success("✅ ¡Perfecto! Ahora Alameda está blindada en un solo bloque.")
    else:
        st.info("Sube archivos.")

if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_Final.zip", "application/zip", type="primary")
