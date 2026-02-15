import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import plotly.express as px  # NUEVO: Para graficar

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Visual V109", layout="wide")
st.title("🚛 Logística ITA RADIAN: Monitor de Territorios")

# --- ESTILOS CSS (Para que se vea como te gusta) ---
st.markdown("""
    <style>
    .stExpander { border: 1px solid #003366; border-radius: 5px; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- CEREBRO MAESTRO DEFAULT ---
MAESTRA_DEFAULT = {
    # TECNICO 1
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", "SANTA MONICA": "TECNICO 1",
    "BELLARENA": "TECNICO 1", "EL PARQUE": "TECNICO 1", "LA ALBORAYA": "TECNICO 1", "EL CAMPITO": "TECNICO 1",
    "LA MAGDALENA": "TECNICO 1", "PASADENA": "TECNICO 1", "EL LIMON": "TECNICO 1", "LA CHINITA": "TECNICO 1",
    "LA LUZ": "TECNICO 1", "LAS NIEVES": "TECNICO 1", "LA UNION": "TECNICO 1", "LAS PALMAS": "TECNICO 1",
    "VILLA DEL CARMEN": "TECNICO 1", "LOS TRUPILLOS": "TECNICO 1", "SAN NICOLAS": "TECNICO 1",
    "SIMON BOLIVAR": "TECNICO 1", "TAYRONA": "TECNICO 1", "UNIVERSAL": "TECNICO 1", "EL MILAGRO": "TECNICO 1",
    "ALAMEDA DEL RIO": "TECNICO 1", "CARIBE VERDE": "TECNICO 1", "VILLAS DE SAN PABLO": "TECNICO 1",
    
    # TECNICO 2
    "COLOMBIA": "TECNICO 2", "EL PORVENIR": "TECNICO 2", "LA FLORIDA": "TECNICO 2", "SAN FELIPE": "TECNICO 2",
    "NUEVA GRANADA": "TECNICO 2", "SAN FRANCISCO": "TECNICO 2", "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2",
    "ALTOS DE RIOMAR": "TECNICO 2", "EL GOLF": "TECNICO 2", "SAN VICENTE": "TECNICO 2", "EL POBLADO": "TECNICO 2",
    "GRANADILLO": "TECNICO 2", "VILLA CAROLINA": "TECNICO 2", "PARAISO": "TECNICO 2", "SAN SALVADOR": "TECNICO 2",
    
    # TECNICO 3
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3", "CAMPO ALEGRE": "TECNICO 3",
    "LAS ESTRELLAS": "TECNICO 3", "CIUDAD JARDIN": "TECNICO 3", "MERCEDES": "TECNICO 3", "LOS ALPES": "TECNICO 3",
    
    # TECNICO 4
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4", "MODELO": "TECNICO 4",
    "MONTECRISTO": "TECNICO 4", "BELLAVISTA": "TECNICO 4", "SANTA ANA": "TECNICO 4", "LA CONCEPCION": "TECNICO 4",
    
    # TECNICO 5
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5", "LA MANGA": "TECNICO 5",
    "MEQUEJO": "TECNICO 5", "POR FIN": "TECNICO 5", "LA ESMERALDA": "TECNICO 5", "VILLA SAN PEDRO": "TECNICO 5",
    "LAS MALVINAS": "TECNICO 5",
    
    # TECNICO 6
    "CALIFORNIA": "TECNICO 6", "VILLAS DE LA CORDIALIDAD": "TECNICO 6", "METRO PARQUE": "TECNICO 6",
    "LA PAZ": "TECNICO 6", "LOS ROSALES": "TECNICO 6", "VILLA DEL ROSARIO": "TECNICO 6",
    "EL PUEBLO": "TECNICO 6", "EL ROMANCE": "TECNICO 6", "CIUDAD MODESTO": "TECNICO 6",
    "LA GLORIA": "TECNICO 6", "LA CORDIALIDAD": "TECNICO 6",
    
    # TECNICO 7
    "ATLANTICO": "TECNICO 7", "BOYACA": "TECNICO 7", "CHIQUINQUIRA": "TECNICO 7", "SAN ROQUE": "TECNICO 7",
    
    # TECNICO 8
    "LAS FLORES": "TECNICO 8", "SIAPE": "TECNICO 8", "VILLA FLORENCIA": "TECNICO 8"
}

# --- VECINDAD ---
VECINOS_LOGICOS = {
    "TECNICO 1": ["TECNICO 7", "TECNICO 6", "TECNICO 2"],
    "TECNICO 2": ["TECNICO 4", "TECNICO 3", "TECNICO 8"],
    "TECNICO 3": ["TECNICO 2", "TECNICO 5", "TECNICO 4"],
    "TECNICO 4": ["TECNICO 2", "TECNICO 7", "TECNICO 3"],
    "TECNICO 5": ["TECNICO 6", "TECNICO 3", "TECNICO 1"],
    "TECNICO 6": ["TECNICO 5", "TECNICO 1", "TECNICO 3"],
    "TECNICO 7": ["TECNICO 1", "TECNICO 4", "TECNICO 6"],
    "TECNICO 8": ["TECNICO 2", "TECNICO 4", "TECNICO 1"]
}

# --- FUNCIONES ---
def limpiar_texto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def cargar_maestro(file):
    nuevo_mapa = MAESTRA_DEFAULT.copy()
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        for _, row in df.iterrows():
            b = limpiar_texto(str(row.iloc[0]))
            t = limpiar_texto(str(row.iloc[1]))
            nuevo_mapa[b] = t
    except: pass
    return nuevo_mapa

VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'BIS': 0.05}
def calcular_peso_direccion(dir_text):
    texto = limpiar_texto(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0) if match else 0.0
    if "SUR" in texto: peso -= 5000 
    return peso

class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - CONTROL DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf_horizontal(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 60, 90, 60]
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 10)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for h, w in zip(headers, widths):
            col_real = col_map.get(h)
            val = str(row[col_real])[:45] if col_real else ""
            try: val = val.encode('latin-1', 'replace').decode('latin-1')
            except: pass
            pdf.cell(w, 8, val, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- ESTADO ---
if 'mapa_barrios' not in st.session_state: st.session_state['mapa_barrios'] = MAESTRA_DEFAULT
if 'zip_generado' not in st.session_state: st.session_state['zip_generado'] = None

# --- SIDEBAR (CONFIGURACIÓN) ---
st.sidebar.header("🎛️ Panel de Control")
MAX_CUPO = st.sidebar.number_input("Cupo Máximo", value=35)
maestro_up = st.sidebar.file_uploader("Actualizar Barrios", type=["xlsx", "csv"])
if maestro_up:
    st.session_state['mapa_barrios'] = cargar_maestro(maestro_up)
    st.sidebar.success("✅ Actualizado")

st.sidebar.subheader("Técnicos Activos")
tecnicos_unicos = sorted(list(set(st.session_state['mapa_barrios'].values())))
TECNICOS_ACTIVOS = []
for tec in tecnicos_unicos:
    if st.sidebar.checkbox(tec, value=True): TECNICOS_ACTIVOS.append(tec)

# --- VISUALIZADOR DE TERRITORIO (GRÁFICO) ---
with st.expander("🗺️ Ver Mapa de Territorios (Quien cubre qué)", expanded=True):
    # Crear DataFrame para el gráfico
    data_mapa = []
    for barrio, tecnico in st.session_state['mapa_barrios'].items():
        data_mapa.append({"Tecnico": tecnico, "Barrio": barrio, "Valor": 1})
    df_mapa = pd.DataFrame(data_mapa)
    
    # Gráfico Treemap
    fig = px.treemap(
        df_mapa, 
        path=['Tecnico', 'Barrio'], 
        values='Valor',
        title='Distribución de Barrios por Técnico (Barranquilla)',
        color='Tecnico',
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig.update_layout(margin=dict(t=30, l=0, r=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- CARGA DE ARCHIVOS ---
col1, col2 = st.columns(2)
with col1: pdf_file = st.file_uploader("1. PDF Pólizas", type="pdf")
with col2: excel_file = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])

if excel_file:
    try:
        if excel_file.name.endswith('.csv'): df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
        else: df = pd.read_excel(excel_file)
        df.columns = [limpiar_texto(c) for c in df.columns]

        def find_col(k_list):
            for k in k_list:
                for c in df.columns:
                    if k in c: return c
            return None
        col_barrio = find_col(['BARRIO', 'SECTOR'])
        col_cta = find_col(['CUENTA', 'POLIZA', 'NRO'])
        col_dir = find_col(['DIRECCION', 'DIR'])

        if col_barrio and col_cta:
            # PRE-ASIGNACIÓN
            def pre_asignar(b):
                b_clean = limpiar_texto(str(b))
                # Búsqueda
                if b_clean in st.session_state['mapa_barrios']: return st.session_state['mapa_barrios'][b_clean]
                for k, v in st.session_state['mapa_barrios'].items():
                    if k in b_clean: return v
                return "SIN_ASIGNAR"
            
            df['TECNICO_PREVIO'] = df[col_barrio].apply(pre_asignar)
            
            # --- GRÁFICO DE COBERTURA EN VIVO ---
            st.divider()
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("📊 Cobertura Hoy")
                conteo_previo = df['TECNICO_PREVIO'].value_counts().reset_index()
                conteo_previo.columns = ['Estado', 'Ordenes']
                
                # Gráfico de Torta para ver qué no se cubre
                fig_pie = px.pie(conteo_previo, names='Estado', values='Ordenes', hole=0.4, title="Asignación Inicial")
                # Resaltar SIN_ASIGNAR en rojo
                colors = {'SIN_ASIGNAR': 'red'}
                fig_pie.update_traces(marker=dict(colors=[colors.get(x, '#003366') for x in conteo_previo['Estado']]))
                st.plotly_chart(fig_pie, use_container_width=True)
                
                if "SIN_ASIGNAR" in conteo_previo['Estado'].values:
                    st.error("⚠️ Hay barrios sin técnico asignado. Revisa el gráfico.")
                else:
                    st.success("✅ Todos los barrios tienen cobertura.")

            with c2:
                st.subheader("📋 Detalle de Órdenes")
                st.dataframe(df[[col_barrio, 'TECNICO_PREVIO', col_cta]].head(100), height=350)

            # --- BOTÓN DE ACCIÓN ---
            if pdf_file:
                if st.button("🚀 Confirmar y Generar ZIP", type="primary"):
                    with st.spinner("Balanceando cargas y generando archivos..."):
                        # BALANCEO
                        conteo_real = {t: 0 for t in TECNICOS_ACTIVOS}
                        asig_final = []
                        df = df.sort_values(by=['TECNICO_PREVIO', col_barrio])

                        for _, row in df.iterrows():
                            ideal = row['TECNICO_PREVIO']
                            asignado = "SIN_ASIGNAR"
                            
                            if ideal in TECNICOS_ACTIVOS:
                                if conteo_real[ideal] < MAX_CUPO:
                                    asignado = ideal
                                    conteo_real[ideal] += 1
                                else:
                                    vecinos = VECINOS_LOGICOS.get(ideal, [])
                                    found = False
                                    for v in vecinos:
                                        if v in TECNICOS_ACTIVOS and conteo_real[v] < MAX_CUPO:
                                            asignado = f"{v} (APOYO)"
                                            conteo_real[v] += 1
                                            found = True; break
                                    if not found: asignado = f"{ideal} (EXTRA)"
                            elif "TECNICO" in ideal: 
                                vecinos = VECINOS_LOGICOS.get(ideal, [])
                                found = False
                                for v in vecinos:
                                    if v in TECNICOS_ACTIVOS and conteo_real[v] < MAX_CUPO:
                                        asignado = f"{v} (COBERTURA)"
                                        conteo_real[v] += 1
                                        found = True; break
                                if not found: asignado = "SIN_GESTOR_ACTIVO"
                            else: asignado = "ZONA_DESCONOCIDA"
                            
                            asig_final.append(asignado)
                        
                        df['TECNICO_REAL'] = asig_final
                        df['CARPETA'] = df['TECNICO_REAL'].apply(lambda x: x.split(" (")[0])

                        # PDF
                        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                        mapa_pdfs = {}
                        i = 0
                        while i < len(doc):
                            txt = doc[i].get_text()
                            match = re.search(r"Póliza\s*No:?\s*(\d+)", txt, re.IGNORECASE)
                            if match:
                                pid = match.group(1)
                                pgs = [i]
                                while i+1 < len(doc):
                                    if "Póliza No" not in doc[i+1].get_text(): pgs.append(i+1); i+=1
                                    else: break
                                sub = fitz.open()
                                for p in pgs: sub.insert_pdf(doc, from_page=p, to_page=p)
                                mapa_pdfs[pid] = sub.tobytes()
                                sub.close()
                            i += 1
                        
                        # ZIP
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            out_tot = io.BytesIO()
                            with pd.ExcelWriter(out_tot, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
                            zf.writestr("0_BASE_TOTAL.xlsx", out_tot.getvalue())

                            col_map = {'CUENTA': col_cta, 'MEDIDOR': find_col(['MEDIDOR']), 'BARRIO': col_barrio, 'DIRECCION': col_dir, 'CLIENTE': find_col(['CLIENTE'])}

                            for tec in df['CARPETA'].unique():
                                if "SIN_" in tec or "ZONA_" in tec: continue
                                safe_tec = limpiar_texto(tec).replace(" ", "_")
                                df_t = df[df['CARPETA'] == tec].copy()
                                if col_dir:
                                    df_t['PESO'] = df_t[col_dir].astype(str).apply(calcular_peso_direccion)
                                    df_t = df_t.sort_values(by=[col_barrio, 'PESO'], ascending=[True, False])

                                pdf_h = crear_pdf_horizontal(df_t, tec, col_map)
                                zf.writestr(f"{safe_tec}/1_LISTADO.pdf", pdf_h)
                                
                                out_t = io.BytesIO()
                                with pd.ExcelWriter(out_t, engine='xlsxwriter') as writer: df_t.drop(columns=['PESO'] if 'PESO' in df_t else []).to_excel(writer, index=False)
                                zf.writestr(f"{safe_tec}/2_DIGITAL.xlsx", out_t.getvalue())
                                
                                merge = fitz.open()
                                found = False
                                for _, row in df_t.iterrows():
                                    cta = str(row[col_cta])
                                    pdf_d = None
                                    for k, v in mapa_pdfs.items():
                                        if k in cta: pdf_d = v; break
                                    if pdf_d:
                                        found = True
                                        zf.writestr(f"{safe_tec}/POLIZAS/Poliza_{cta}.pdf", pdf_d)
                                        with fitz.open(stream=pdf_d, filetype="pdf") as tmp: merge.insert_pdf(tmp)
                                if found: zf.writestr(f"{safe_tec}/3_IMPRESION.pdf", merge.tobytes())
                                merge.close()
                        
                        st.session_state['zip_generado'] = zip_buffer.getvalue()
                        st.success("✅ Proceso Terminado.")
        else: st.error("Faltan columnas en el Excel.")
    except Exception as e: st.error(f"Error: {e}")

if st.session_state['zip_generado']:
    st.download_button("⬇️ Descargar ZIP Final", st.session_state['zip_generado'], "Logistica_ITA.zip", "application/zip", type="primary")
