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

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Dinámica V119", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    .error-box { background-color: #7d1b1b; padding: 15px; border-radius: 5px; color: #ffcccc; border: 1px solid #ff4b4b; margin-bottom: 15px;}
    .success-box { background-color: #1b4d3e; padding: 10px; border-radius: 5px; color: #ccffdd; border: 1px solid #00cc66;}
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Asignación Elástica")

# --- 1. ESTADO INICIAL (GENÉRICO) ---
# Esto es lo que se usa si NO subes el archivo de operarios.
MAESTRA_GENERICA = {
    # Zona 1
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", 
    # Zona 2
    "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2", "LAS FLORES": "TECNICO 2",
    # Zona 3
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3",
    # Zona 4
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4",
    # Zona 5
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5",
    # Zona 6
    "LA PAZ": "TECNICO 6", "CARIBE VERDE": "TECNICO 6", "VILLAS DE SAN PABLO": "TECNICO 6",
    # Zona 7
    "LAS NIEVES": "TECNICO 7", "SIMON BOLIVAR": "TECNICO 7", "LA CHINITA": "TECNICO 7",
    # Zona 8
    "VILLA FLORENCIA": "TECNICO 8", "SIAPE": "TECNICO 8"
}

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def limpiar_flexible(txt):
    txt = limpiar_estricto(txt)
    txt = re.sub(r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|ZONA|BRR)\b', '', txt).strip()
    return txt

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(barrio_input)
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    b_flex = limpiar_flexible(barrio_input)
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    # Búsqueda contenida
    for k_maestro, tecnico in mapa_barrios.items():
        if k_maestro == b_flex: return tecnico
        if len(k_maestro) > 4 and k_maestro in b_raw: return tecnico
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        
        # Detectar columnas (Asumimos 1=Barrio, 2=Tecnico)
        col_barrio = df.columns[0]
        col_tec = df.columns[1]
        
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tec]).upper().strip()
            # Validar que el nombre del técnico sea válido
            if t and t != "NAN" and t != "":
                mapa[b] = t
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return MAESTRA_GENERICA
    return mapa

# --- ALGORITMO ORDENAMIENTO ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'BIS': 0.05}
def calcular_peso_js(txt):
    clean = limpiar_estricto(txt)
    penalidad = 5000 if "SUR" in clean else 0
    nums = re.findall(r'(\d+)', clean)
    ref = int(nums[0]) if nums else 0
    if "CL" in clean or "CALLE" in clean: peso = (110 - ref) * 1000
    else: peso = ref * 1000
    secundario = int(nums[1]) if len(nums) > 1 else 0
    return peso + secundario + penalidad

class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 60, 90, 60]
    pdf.set_fill_color(200, 200, 200)
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

# --- SESSION STATE ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = MAESTRA_GENERICA
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None
if 'log_cambios' not in st.session_state: st.session_state['log_cambios'] = None

# ------------------------------------------------------------------
# 👷 PANEL LATERAL ELÁSTICO
# ------------------------------------------------------------------
st.sidebar.header("👷 Cuadrilla Detectada")

# 1. Extraer nombres únicos del mapa actual
# Si es el default, saldrá TECNICO 1..8. Si cargaste Excel, saldrán los nombres reales.
lista_tecnicos_detectados = sorted(list(set(st.session_state['mapa_actual'].values())))
TECNICOS_ACTIVOS = []

st.sidebar.caption(f"Se encontraron {len(lista_tecnicos_detectados)} perfiles en la base de datos.")

# 2. Generar Toggles Dinámicos
st.sidebar.markdown("---")
# Botón maestro
all_selected = st.sidebar.checkbox("Seleccionar Todos", value=True)

for tec in lista_tecnicos_detectados:
    # Si hay muchos (más de 10), usamos un checkbox compacto, si son pocos, toggle
    is_active = st.sidebar.toggle(f"✅ {tec}", value=all_selected)
    if is_active:
        TECNICOS_ACTIVOS.append(tec)

st.sidebar.markdown("---")
st.sidebar.write(f"**Trabajando hoy:** {len(TECNICOS_ACTIVOS)}")

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Operación", "📊 Resultados", "⚙️ Cargar Personal"])

# --- TAB 3: CARGA MAESTRA ---
with tab3:
    st.header("Actualizar Base de Operarios")
    st.markdown("""
    Sube aquí tu archivo `OPERARIOS_REINSTALACIONES.xlsx`. 
    - El sistema detectará automáticamente los nombres.
    - Si agregas un técnico nuevo en el Excel, aparecerá automáticamente en el menú.
    """)
    maestro_file = st.file_uploader("Subir Maestro (Barrio | Técnico)", type=["xlsx", "csv"])
    
    if maestro_file:
        # Cargar y actualizar estado
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
        
        # Detectar nuevos
        nuevos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
        
        st.success(f"✅ ¡Base Actualizada! Detectados {len(nuevos_tecnicos)} operarios.")
        st.dataframe(pd.DataFrame(nuevos_tecnicos, columns=["Nombres Detectados"]), height=200)

# --- TAB 1: OPERACIÓN ---
with tab1:
    col_in1, col_in2 = st.columns(2)
    with col_in1: pdf_in = st.file_uploader("1. PDF Pólizas", type="pdf")
    with col_in2: excel_in = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])
    
    if excel_in:
        try:
            if excel_in.name.endswith('.csv'): df = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
            else: df = pd.read_excel(excel_in)
            df.columns = [limpiar_estricto(c) for c in df.columns]

            def find(k):
                for x in k:
                    for c in df.columns: 
                        if x in c: return c
                return None
            
            c_barrio = find(['BARRIO', 'SECTOR'])
            c_cta = find(['CUENTA', 'POLIZA', 'NRO'])
            c_dir = find(['DIRECCION', 'DIR'])

            if c_barrio and c_cta:
                # ASIGNACIÓN
                df['TECNICO_IDEAL'] = df[c_barrio].apply(lambda x: buscar_tecnico_exacto(str(x), st.session_state['mapa_actual']))
                
                # RECOMENDADOR
                num_ordenes = len(df)
                num_activos = len(TECNICOS_ACTIVOS)
                recomendado = math.ceil(num_ordenes / num_activos) if num_activos > 0 else 35
                
                st.divider()
                st.subheader("⚖️ Configuración")
                TOPE = st.number_input(f"Tope Máximo (Sugerido: {recomendado})", value=recomendado)
                
                # ALERTA
                sin_asignar = df[df['TECNICO_IDEAL'] == "SIN_ASIGNAR"]
                if not sin_asignar.empty:
                    st.markdown(f"""<div class="error-box">⚠️ ALERTA: {len(sin_asignar)} barrios desconocidos. Actualiza la Pestaña 3.</div>""", unsafe_allow_html=True)
                    st.dataframe(sin_asignar[[c_barrio]].drop_duplicates(), use_container_width=True)

                if pdf_in:
                    if st.button("🚀 PROCESAR DESPACHO", type="primary"):
                        with st.spinner("Balanceando cargas dinámicamente..."):
                            
                            df = df.sort_values(by=['TECNICO_IDEAL', c_barrio])
                            conteo_real = {t: 0 for t in TECNICOS_ACTIVOS}
                            asignacion_final = []
                            log_cambios = []
                            
                            for _, row in df.iterrows():
                                ideal = row['TECNICO_IDEAL']
                                bar = row[c_barrio]
                                final = "SIN_ASIGNAR"
                                
                                if "SIN_ASIGNAR" in ideal:
                                    final = "SIN_ASIGNAR"
                                else:
                                    # 1. Asignar al Ideal si activo y con cupo
                                    if ideal in TECNICOS_ACTIVOS and conteo_real[ideal] < TOPE:
                                        final = ideal
                                        conteo_real[ideal] += 1
                                    else:
                                        # 2. DESBORDE INTELIGENTE (Sin vecinos fijos)
                                        # Buscar el técnico activo con MENOR carga actual
                                        # Esto permite que funcione con nombres nuevos sin configurar vecinos
                                        candidatos = [t for t in TECNICOS_ACTIVOS if conteo_real[t] < TOPE]
                                        
                                        if candidatos:
                                            # Ordenar candidatos por quién está más libre
                                            mejor_opcion = sorted(candidatos, key=lambda x: conteo_real[x])[0]
                                            final = f"{mejor_opcion} (BALANCEO)"
                                            conteo_real[mejor_opcion] += 1
                                            
                                            motivo = "Cupo Lleno" if ideal in TECNICOS_ACTIVOS else "Ausente"
                                            log_cambios.append({"Barrio": bar, "Razón": motivo, "Original": ideal, "Nuevo": mejor_opcion})
                                        else:
                                            final = f"{ideal} (EXTRA)" # Todos llenos

                                asignacion_final.append(final)
                            
                            df['TECNICO_REAL'] = asignacion_final
                            df['CARPETA'] = df['TECNICO_REAL'].apply(lambda x: x.split(" (")[0])
                            
                            st.session_state['log_cambios'] = pd.DataFrame(log_cambios)
                            
                            # PDF Processing
                            doc = fitz.open(stream=pdf_in.read(), filetype="pdf")
                            mapa_p = {}
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
                                    mapa_p[pid] = sub.tobytes()
                                    sub.close()
                                i += 1
                            
                            # ZIP Generation
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w") as zf:
                                # Backup
                                for pk, pb in mapa_p.items():
                                    zf.writestr(f"00_TODOS_LOS_PDFS/Poliza_{pk}.pdf", pb)
                                
                                out_base = io.BytesIO()
                                with pd.ExcelWriter(out_base, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                                zf.writestr("01_CONSOLIDADO_GENERAL.xlsx", out_base.getvalue())
                                
                                c_map = {'CUENTA': c_cta, 'MEDIDOR': find(['MEDIDOR']), 'BARRIO': c_barrio, 'DIRECCION': c_dir, 'CLIENTE': find(['CLIENTE'])}
                                
                                for tec in df['CARPETA'].unique():
                                    if "SIN_" in tec: continue
                                    safe = str(tec).replace(" ","_")
                                    df_t = df[df['CARPETA'] == tec].copy()
                                    if c_dir:
                                        df_t['P'] = df_t[c_dir].astype(str).apply(calcular_peso_js)
                                        df_t = df_t.sort_values('P')
                                    
                                    pdf_h = crear_pdf(df_t, tec, c_map)
                                    zf.writestr(f"{safe}/1_LISTADO.pdf", pdf_h)
                                    
                                    out_t = io.BytesIO()
                                    with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                                    zf.writestr(f"{safe}/2_DIGITAL.xlsx", out_t.getvalue())
                                    
                                    m = fitz.open()
                                    f = False
                                    for _, r in df_t.iterrows():
                                        c = str(r[c_cta])
                                        d = None
                                        for k,v in mapa_p.items():
                                            if k in c: d=v; break
                                        if d:
                                            f=True
                                            zf.writestr(f"{safe}/POLIZAS/Poliza_{c}.pdf", d)
                                            with fitz.open(stream=d, filetype="pdf") as t: m.insert_pdf(t)
                                    if f: zf.writestr(f"{safe}/3_IMPRESION.pdf", m.tobytes())
                                    m.close()

                            st.session_state['zip_listo'] = zip_buffer.getvalue()
                            st.success("✅ ¡Proceso Terminado!")
            else:
                st.warning("⚠️ Sube el Excel para continuar.")
        except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: LOG ---
with tab2:
    st.header("Historial de Movimientos")
    if st.session_state['log_cambios'] is not None and not st.session_state['log_cambios'].empty:
        st.dataframe(st.session_state['log_cambios'], use_container_width=True)
    else:
        st.info("Sin movimientos.")

# --- DESCARGA ---
if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_Dinamica.zip", "application/zip", type="primary")
