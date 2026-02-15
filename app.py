###############################################################################
#                                                                             #
#   SISTEMA INTEGRAL DE LOGÍSTICA ITA (WEB + ZIP)                             #
#   VERSION: 3.0 FINAL                                                        #
#   ARQUITECTURA: MONOLITO HÍBRIDO (ADMINISTRACIÓN + AUTOGESTIÓN)             #
#                                                                             #
#   CARACTERÍSTICAS BLINDADAS:                                                #
#   1. ORDENAMIENTO: Algoritmo de Tuplas (Natural Sort) INTACTO.              #
#   2. ESTRUCTURA ZIP: 4 Carpetas (1_Ruta, 2_Tabla, 3_Leg, 4_Polizas).        #
#   3. PORTAL WEB: Técnicos descargan solo Ruta y Legalización.               #
#   4. PERSISTENCIA: Sistema de archivos temporal para publicación.           #
#                                                                             #
###############################################################################

import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import os
import shutil
import time

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Logística ITA V3.0",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded"
)

# Estilos CSS Profesionales (Botones Grandes y Colores Corporativos)
st.markdown("""
    <style>
    /* Fondo y Fuente */
    .stApp { background-color: #0E1117; color: #FAFAFA; font-family: 'Segoe UI', sans-serif; }
    
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        height: 55px; 
        background-color: #1F2937; 
        color: white; 
        border-radius: 8px; 
        border: 1px solid #374151;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border: 2px solid #60A5FA; 
    }
    
    /* Botones de Acción (Procesar/Publicar) */
    div.stButton > button:first-child { 
        background-color: #2563EB; 
        color: white; 
        border-radius: 8px; 
        height: 55px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #1D4ED8;
        transform: translateY(-2px);
    }

    /* Botones de Descarga (Verdes) */
    div.stDownloadButton > button:first-child { 
        background-color: #059669; 
        color: white; 
        border-radius: 8px; 
        height: 60px; 
        width: 100%; 
        font-size: 18px;
        font-weight: bold;
        border: 1px solid #34D399;
    }
    div.stDownloadButton > button:first-child:hover {
        background-color: #047857;
    }

    /* Alertas y Métricas */
    div[data-testid="stMetricValue"] { color: #60A5FA; }
    .stAlert { background-color: #1F2937; border: 1px solid #374151; color: #E5E7EB; }
    
    /* Títulos Personalizados */
    .header-tecnico {
        font-size: 28px;
        font-weight: bold;
        color: #34D399;
        margin-bottom: 10px;
        text-align: center;
        border-bottom: 2px solid #34D399;
        padding-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SISTEMA DE ARCHIVOS (CARPETA PÚBLICA)
# =============================================================================

# Carpeta donde se "Publican" los archivos para que los técnicos los vean
CARPETA_PUBLICA = "public_files"

def inicializar_sistema_archivos():
    """Crea la carpeta pública si no existe."""
    if not os.path.exists(CARPETA_PUBLICA):
        os.makedirs(CARPETA_PUBLICA)

def limpiar_carpeta_publica():
    """Borra todo el contenido viejo antes de publicar nuevas rutas."""
    if os.path.exists(CARPETA_PUBLICA):
        shutil.rmtree(CARPETA_PUBLICA)
    os.makedirs(CARPETA_PUBLICA)

inicializar_sistema_archivos()

# =============================================================================
# 3. FUNCIONES DE PROCESAMIENTO (TU CÓDIGO INTACTO)
# =============================================================================

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
        # Normalización de columnas
        df.columns = [str(c).upper().strip() for c in df.columns]
        c_b = df.columns[0]
        c_t = df.columns[1]
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_b]))
            t = str(row[c_t]).upper().strip()
            if t and t != "NAN": mapa[b] = t
    except: pass
    return mapa

# --- ALGORITMO DE ORDENAMIENTO (CORREGIDO PARA EVITAR ERROR DE LISTA) ---
def natural_sort_key(txt):
    """Devuelve una tupla (hashable) para evitar el error de list unhashable."""
    if not txt: return tuple()
    txt = str(txt).upper()
    # Convertimos a tupla para que Pandas pueda procesarlo sin errores
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# =============================================================================
# 4. GENERACIÓN DE PDF (CLASE FPDF)
# =============================================================================

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
            return str(row[col_name]) if col_name and col_name != "NO TIENE" else ""

        data_row = [str(idx), get_val('CUENTA'), get_val('MEDIDOR')[:15], barrio_txt[:35], get_val('DIRECCION')[:50], get_val('CLIENTE')[:30]]
        
        for val, w in zip(data_row, widths):
            try: val_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_enc = val
            pdf.cell(w, 7, val_enc, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# =============================================================================
# 5. ESTADO DE LA SESIÓN (SESSION STATE)
# =============================================================================

if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None

# =============================================================================
# 6. INTERFAZ PRINCIPAL - BARRA LATERAL (ROL)
# =============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942813.png", width=80)
    st.title("SISTEMA LOGÍSTICO")
    st.markdown("---")
    modo = st.radio("Selecciona tu Perfil:", ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"])
    st.markdown("---")
    st.caption("Versión 3.0 Final - ITA Radian")

# =============================================================================
# 7. VISTA DEL TÉCNICO (DESCARGA SIMPLE)
# =============================================================================

if modo == "👷 TÉCNICO":
    st.markdown('<div class="header-tecnico">🚛 ZONA DE DESCARGA</div>', unsafe_allow_html=True)
    st.write("Bienvenido. Busca tu nombre en la lista para descargar tus documentos del día.")
    st.info("Recuerda: Aquí descargas la **Hoja de Ruta** y el **Paquete de Legalización**.")
    
    st.markdown("---")
    
    # Buscar carpetas de técnicos en la carpeta pública
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_disponibles = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    else:
        tecnicos_disponibles = []
        
    if not tecnicos_disponibles:
        st.warning("⏳ Aún no hay rutas publicadas. Por favor espera a que el administrador publique.")
        if st.button("🔄 Recargar Página"): st.rerun()
    else:
        seleccion = st.selectbox("👇 SELECCIONA TU NOMBRE:", ["-- Seleccionar --"] + tecnicos_disponibles)
        
        if seleccion != "-- Seleccionar --":
            ruta_tec = os.path.join(CARPETA_PUBLICA, seleccion)
            
            # Buscar archivos específicos
            archivo_ruta = os.path.join(ruta_tec, "1_HOJA_DE_RUTA.pdf")
            archivo_leg = os.path.join(ruta_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            col1, col2 = st.columns(2)
            
            # BOTÓN 1: HOJA DE RUTA
            with col1:
                st.markdown("#### 📄 Listado de Visitas")
                if os.path.exists(archivo_ruta):
                    with open(archivo_ruta, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR RUTA",
                            data=f,
                            file_name=f"Ruta_{seleccion}.pdf",
                            mime="application/pdf",
                            key="btn_ruta"
                        )
                else:
                    st.error("No disponible")

            # BOTÓN 2: PAQUETE LEGALIZACIÓN
            with col2:
                st.markdown("#### 📂 Pólizas (Paquete)")
                if os.path.exists(archivo_leg):
                    with open(archivo_leg, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR LEGALIZACIÓN",
                            data=f,
                            file_name=f"Legalizacion_{seleccion}.pdf",
                            mime="application/pdf",
                            key="btn_leg"
                        )
                else:
                    st.warning("No tienes pólizas hoy")

# =============================================================================
# 8. VISTA DEL ADMINISTRADOR (PANEL DE CONTROL)
# =============================================================================

elif modo == "⚙️ ADMINISTRADOR":
    st.header("⚙️ Panel de Gestión Logística")
    password = st.text_input("Contraseña de Acceso", type="password")
    
    if password == "ita2026": # CLAVE DE ACCESO
        
        tab_base, tab_proceso, tab_publicar = st.tabs(["1. Base Operarios", "2. Carga y Balanceo", "3. Publicar y Descargar"])
        
        # --- PESTAÑA 1: BASE DE DATOS ---
        with tab_base:
            st.subheader("Cargar Maestro de Técnicos")
            maestro_file = st.file_uploader("Subir Excel (Barrio | Técnico)", type=["xlsx", "csv"])
            if maestro_file:
                st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
                st.success(f"✅ Maestro cargado con {len(st.session_state['mapa_actual'])} barrios.")
            
            if st.session_state['mapa_actual']:
                st.metric("Técnicos Activos", len(set(st.session_state['mapa_actual'].values())))
        
        # --- PESTAÑA 2: CARGA Y PROCESAMIENTO ---
        with tab_proceso:
            st.subheader("Cargar Insumos Diarios")
            
            c1, c2 = st.columns(2)
            with c1: pdf_in = st.file_uploader("1. PDF Pólizas (Completo)", type="pdf")
            with c2: excel_in = st.file_uploader("2. Excel Ruta (CSV/XLSX)", type=["xlsx", "csv"])
            
            # Procesamiento de Pólizas (Solo si se sube nuevo PDF)
            if pdf_in:
                if st.button("🔄 Procesar PDF de Pólizas (Extraer)"):
                    with st.spinner("Escaneando PDF... esto puede tardar unos segundos"):
                        pdf_in.seek(0)
                        doc = fitz.open(stream=pdf_in.read(), filetype="pdf")
                        temp_mapa = {}
                        for i in range(len(doc)):
                            txt = doc[i].get_text()
                            regex = r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})'
                            if matches := re.findall(regex, txt, re.IGNORECASE):
                                sub = fitz.open()
                                sub.insert_pdf(doc, from_page=i, to_page=i)
                                # Lógica de página siguiente si es anexo
                                if i + 1 < len(doc):
                                    txt_next = doc[i+1].get_text()
                                    if not re.search(r'(?:Póliza|Poliza|Cuenta)', txt_next, re.IGNORECASE):
                                        sub.insert_pdf(doc, from_page=i+1, to_page=i+1)
                                pdf_bytes = sub.tobytes()
                                sub.close()
                                for m in matches: temp_mapa[normalizar_numero(m)] = pdf_bytes
                        st.session_state['mapa_polizas_cargado'] = temp_mapa
                        st.success(f"✅ PDF Procesado. {len(temp_mapa)} pólizas detectadas.")
            
            # Procesamiento del Excel de Ruta
            lista_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            if excel_in and lista_tecnicos:
                try:
                    if excel_in.name.endswith('.csv'): df_raw = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
                    else: df_raw = pd.read_excel(excel_in)
                    cols = list(df_raw.columns)
                    
                    st.divider()
                    st.write("Configuración de Cupos y Columnas")
                    
                    # Topes
                    df_topes = pd.DataFrame({"Técnico": lista_tecnicos, "Cupo": [35]*len(lista_tecnicos)})
                    ed_topes = st.data_editor(df_topes, column_config={"Cupo": st.column_config.NumberColumn(min_value=1, max_value=200)}, hide_index=True)
                    LIMITES = dict(zip(ed_topes["Técnico"], ed_topes["Cupo"]))
                    
                    # Mapeo
                    def idx(k): 
                        for i, c in enumerate(cols): 
                            for x in k: 
                                if x in str(c).upper(): return i
                        return 0
                    
                    c1, c2, c3 = st.columns(3)
                    s_bar = c1.selectbox("BARRIO", cols, index=idx(['BARRIO','SECTOR']))
                    s_dir = c2.selectbox("DIRECCION", cols, index=idx(['DIR','DIRECCION']))
                    s_cta = c3.selectbox("CUENTA", cols, index=idx(['CUENTA','POLIZA']))
                    s_med = st.selectbox("MEDIDOR", ["NO TIENE"]+cols, index=idx(['MEDIDOR'])+1)
                    s_cli = st.selectbox("CLIENTE", ["NO TIENE"]+cols, index=idx(['CLIENTE'])+1)
                    
                    col_map = {'BARRIO': s_bar, 'DIRECCION': s_dir, 'CUENTA': s_cta, 'MEDIDOR': s_med if s_med!="NO TIENE" else None, 'CLIENTE': s_cli if s_cli!="NO TIENE" else None}
                    
                    if st.button("🚀 EJECUTAR BALANCEO", type="primary"):
                        df = df_raw.copy()
                        df['TECNICO_IDEAL'] = df[s_bar].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                        df['TECNICO_FINAL'] = df['TECNICO_IDEAL']; df['ORIGEN_REAL'] = None
                        
                        # ORDENAMIENTO (TUPLAS)
                        df['SORT_DIR'] = df[s_dir].astype(str).apply(natural_sort_key)
                        df = df.sort_values(by=[s_bar, 'SORT_DIR'])
                        
                        # BALANCEO
                        conteo = df['TECNICO_IDEAL'].value_counts()
                        for giver in [t for t in lista_tecnicos if conteo.get(t, 0) > LIMITES.get(t, 35)]:
                            rows = df[df['TECNICO_FINAL'] == giver]
                            exc = len(rows) - LIMITES.get(giver, 35)
                            if exc > 0:
                                move = rows.index[-exc:]
                                counts = df['TECNICO_FINAL'].value_counts()
                                best = sorted([t for t in lista_tecnicos if t!=giver], key=lambda x: counts.get(x, 0))[0]
                                df.loc[move, 'TECNICO_FINAL'] = best; df.loc[move, 'ORIGEN_REAL'] = giver
                        
                        st.session_state['df_simulado'] = df.drop(columns=['SORT_DIR'])
                        st.session_state['col_map_final'] = col_map
                        st.success("✅ Ruta Balanceada y Ordenada.")
                        
                except Exception as e: st.error(f"Error: {e}")

        # --- PESTAÑA 3: PUBLICACIÓN Y DESCARGA ADMIN ---
        with tab_publicar:
            st.header("Gestión Final")
            
            if st.session_state['df_simulado'] is not None:
                df_final = st.session_state['df_simulado']
                col_map_final = st.session_state['col_map_final']
                mapa_p = st.session_state['mapa_polizas_cargado']
                
                tecnicos_ruta = [t for t in df_final['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                c1, c2 = st.columns(2)
                
                # --- OPCIÓN 1: GENERAR ZIP COMPLETO (PARA EL ADMIN) ---
                with c1:
                    st.subheader("1. Descarga Administrativa (ZIP)")
                    st.info("Genera el ZIP con TODAS las carpetas (1, 2, 3, 4) tal cual lo necesitas.")
                    
                    if st.button("📦 GENERAR ZIP MAESTRO"):
                        with st.spinner("Creando ZIP con estructura completa..."):
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w") as zf:
                                # Consolidado
                                out_b = io.BytesIO()
                                with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df_final.to_excel(w, index=False)
                                zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", out_b.getvalue())
                                
                                # Banco de Pólizas
                                for k, v in mapa_p.items():
                                    zf.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                                
                                # Por técnico
                                for tec in tecnicos_ruta:
                                    safe = str(tec).replace(" ", "_")
                                    # Filtrar y re-ordenar por seguridad
                                    df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                                    df_t['SORT'] = df_t[col_map_final['DIRECCION']].astype(str).apply(natural_sort_key)
                                    df_t = df_t.sort_values(by=[col_map_final['BARRIO'], 'SORT']).drop(columns=['SORT'])
                                    
                                    # 1. Hoja de Ruta
                                    zf.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista(df_t, tec, col_map_final))
                                    
                                    # 2. Tabla Digital
                                    out_t = io.BytesIO()
                                    with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                                    zf.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", out_t.getvalue())
                                    
                                    # 3 y 4. Pólizas
                                    merger = fitz.open()
                                    cnt = 0
                                    for _, r in df_t.iterrows():
                                        cta = normalizar_numero(str(r[col_map_final['CUENTA']]))
                                        if cta in mapa_p:
                                            pdf_bytes = mapa_p[cta]
                                            zf.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{cta}.pdf", pdf_bytes)
                                            with fitz.open(stream=pdf_bytes, filetype="pdf") as tmp: merger.insert_pdf(tmp)
                                            cnt += 1
                                    if cnt > 0:
                                        zf.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                                    merger.close()
                                    
                            st.session_state['zip_admin_ready'] = zip_buffer.getvalue()
                            st.success("ZIP Generado.")
                            
                    if st.session_state['zip_admin_ready']:
                        st.download_button("⬇️ BAJAR ZIP ADMIN", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

                # --- OPCIÓN 2: PUBLICAR EN WEB (PARA LOS TÉCNICOS) ---
                with c2:
                    st.subheader("2. Publicación Web (Técnicos)")
                    st.warning("Esto publicará solo la HOJA DE RUTA y el PAQUETE DE LEGALIZACIÓN en la web.")
                    
                    if st.button("🌍 PUBLICAR PARA TÉCNICOS", type="primary"):
                        limpiar_carpeta_publica()
                        progreso = st.progress(0)
                        
                        for i, tec in enumerate(tecnicos_ruta):
                            # Preparar Carpeta del Técnico
                            safe_name = str(tec).replace(" ", "_")
                            folder_tec = os.path.join(CARPETA_PUBLICA, safe_name)
                            if not os.path.exists(folder_tec): os.makedirs(folder_tec)
                            
                            # Filtrar Datos
                            df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                            df_t['SORT'] = df_t[col_map_final['DIRECCION']].astype(str).apply(natural_sort_key)
                            df_t = df_t.sort_values(by=[col_map_final['BARRIO'], 'SORT']).drop(columns=['SORT'])
                            
                            # 1. GENERAR Y GUARDAR HOJA DE RUTA
                            pdf_bytes = crear_pdf_lista(df_t, tec, col_map_final)
                            with open(os.path.join(folder_tec, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                                f.write(pdf_bytes)
                            
                            # 2. GENERAR Y GUARDAR PAQUETE LEGALIZACIÓN (Solo si hay pólizas)
                            merger = fitz.open()
                            cnt = 0
                            for _, r in df_t.iterrows():
                                cta = normalizar_numero(str(r[col_map_final['CUENTA']]))
                                if cta in mapa_p:
                                    with fitz.open(stream=mapa_p[cta], filetype="pdf") as tmp: merger.insert_pdf(tmp)
                                    cnt += 1
                            
                            if cnt > 0:
                                with open(os.path.join(folder_tec, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f:
                                    f.write(merger.tobytes())
                            merger.close()
                            
                            progreso.progress((i+1)/len(tecnicos_ruta))
                            
                        st.balloons()
                        st.success("✅ ¡RUTAS PUBLICADAS! Dile a los técnicos que entren a descargar.")
                        
            else:
                st.info("Primero procesa la ruta en la pestaña anterior.")

    elif password:
        st.error("Clave incorrecta")
