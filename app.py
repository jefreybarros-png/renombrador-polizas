###############################################################################
#                                                                             #
#   PORTAL LOGÍSTICO ITA - SISTEMA DE GESTIÓN DE RUTAS Y DESCARGA WEB         #
#   VERSION: 2.0 (MODO SERVIDOR)                                              #
#   AUTOR: YEFREY (CONSOLIDADO)                                               #
#                                                                             #
#   ESTE CÓDIGO INCLUYE:                                                      #
#   1. ALGORITMO DE ORDENAMIENTO NATURAL (TUPLAS) PARA BARRIOS                #
#   2. GENERACIÓN DE PDFS CON LIBRERÍA FPDF                                   #
#   3. SISTEMA DE ARCHIVOS INTERNO PARA PUBLICAR RUTAS                        #
#   4. INTERFAZ DUAL: ADMINISTRADOR vs TÉCNICO                                #
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
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Portal Rutas ITA",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded"
)

# Estilos CSS para que se vea profesional y los botones sean grandes
st.markdown("""
    <style>
    /* Fondo oscuro y texto claro */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* Estilos para las pestañas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        height: 55px; 
        background-color: #1F2937; 
        color: white; 
        border-radius: 8px; 
        border: 1px solid #374151;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border: 2px solid #60A5FA; 
    }
    
    /* Botones grandes para celular */
    div.stButton > button:first-child { 
        background-color: #2563EB; 
        color: white; 
        border-radius: 12px; 
        height: 60px; 
        width: 100%; 
        font-size: 20px; 
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #1D4ED8;
        transform: scale(1.02);
    }

    /* Botón de descarga verde */
    div.stDownloadButton > button:first-child { 
        background-color: #059669; 
        color: white; 
        border-radius: 12px; 
        height: 65px; 
        width: 100%; 
        font-size: 22px;
        font-weight: bold;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div.stDownloadButton > button:first-child:hover {
        background-color: #047857;
    }

    /* Contenedores de métricas */
    div[data-testid="metric-container"] {
        background-color: #1F2937;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #374151;
    }
    
    /* Títulos grandes */
    .titulo-principal {
        font-size: 40px;
        font-weight: 800;
        background: -webkit-linear-gradient(left, #60A5FA, #34D399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SISTEMA DE ARCHIVOS (CARPETA PÚBLICA)
# =============================================================================

# Nombre de la carpeta donde se guardarán los PDFs para descarga pública
CARPETA_RUTAS = "rutas_publicas"

# Nos aseguramos de que la carpeta exista al iniciar
if not os.path.exists(CARPETA_RUTAS):
    os.makedirs(CARPETA_RUTAS)

def limpiar_carpeta_publica():
    """
    Borra todos los archivos PDF antiguos de la carpeta pública 
    antes de generar una nueva tanda de rutas.
    """
    for filename in os.listdir(CARPETA_RUTAS):
        file_path = os.path.join(CARPETA_RUTAS, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"No se pudo borrar {file_path}. Razón: {e}")

# =============================================================================
# 3. FUNCIONES DE PROCESAMIENTO DE TEXTO Y DATOS (TU LÓGICA INTACTA)
# =============================================================================

def limpiar_estricto(txt):
    """Limpia tildes y caracteres especiales para búsquedas exactas."""
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """Extrae solo números de una cadena (para cuentas y pólizas)."""
    if not txt: return ""
    nums = re.sub(r'\D', '', str(txt))
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """
    ALGORITMO CLAVE: Ordenamiento natural para direcciones.
    Devuelve una tupla (int, str, int...) para que Python ordene bien
    ej: Calle 2 antes que Calle 10.
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """Busca el barrio en el maestro cargado."""
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(str(barrio_input))
    
    # Intento 1: Exacto
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # Intento 2: Sin palabras clave
    b_flex = re.sub(r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA)\b', '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # Intento 3: Contenido parcial
    for k, v in mapa_barrios.items():
        if k in b_raw: return v
        
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """Carga el Excel de operarios y devuelve el mapa Barrio->Técnico."""
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        # Normalizar encabezados
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Detectar columnas dinámicamente
        c_barrio = df.columns[0] # Asumimos col 1 es barrio
        c_tecnico = df.columns[1] # Asumimos col 2 es técnico

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_barrio]))
            t = str(row[c_tecnico]).upper().strip()
            if t and t != "NAN": 
                mapa[b] = t
    except Exception as e:
        pass
    return mapa

# =============================================================================
# 4. GENERACIÓN DE PDF (CLASE FPDF PERSONALIZADA)
# =============================================================================

class PDFListado(FPDF):
    def header(self):
        # Fondo azul oscuro para el encabezado
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        # Título blanco
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DIGITAL', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista(df, tecnico, col_map):
    """Genera el archivo PDF en memoria (bytes) para un técnico específico."""
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Subtítulo con fecha y total
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    # Encabezados de tabla
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220) # Gris claro
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): 
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Filas de datos
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        
        # Detección de Apoyos (Rojo)
        barrio_txt = str(row[col_map['BARRIO']])
        if pd.notna(row.get('ORIGEN_REAL')):
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0) # Rojo
        else:
            pdf.set_text_color(0, 0, 0) # Negro

        # Obtener valores seguros
        def get_val(key):
            col_name = col_map.get(key)
            return str(row[col_name]) if col_name and col_name != "NO TIENE" else ""

        data_row = [
            str(idx), 
            get_val('CUENTA'), 
            get_val('MEDIDOR')[:15], 
            barrio_txt[:35], 
            get_val('DIRECCION')[:55], 
            get_val('CLIENTE')[:30]
        ]
        
        # Escribir celdas
        for val, w in zip(data_row, widths):
            try: 
                # Manejo de caracteres latinos (tildes/ñ)
                val_enc = val.encode('latin-1', 'replace').decode('latin-1')
            except: 
                val_enc = val
            pdf.cell(w, 7, val_enc, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# =============================================================================
# 5. INICIALIZACIÓN DE VARIABLES DE SESIÓN (ESTADO)
# =============================================================================

if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# =============================================================================
# 6. INTERFAZ PRINCIPAL: BARRA LATERAL (SELECCIÓN DE ROL)
# =============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942813.png", width=80)
    st.title("ITA LOGÍSTICA")
    st.markdown("---")
    
    # Selector de Modo: Admin o Técnico
    modo_acceso = st.radio(
        "¿Quién eres?",
        ["👷 SOY TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0 # Por defecto Técnico para que sea rápido para ellos
    )
    
    st.markdown("---")
    st.info("V 2.0 - Sistema Web")

# =============================================================================
# 7. VISTA DEL TÉCNICO (PORTAL DE DESCARGA)
# =============================================================================

if modo_acceso == "👷 SOY TÉCNICO":
    st.markdown('<div class="titulo-principal">🚛 Portal de Descargas</div>', unsafe_allow_html=True)
    st.write("Selecciona tu nombre en la lista para descargar tu Hoja de Ruta del día.")
    
    st.markdown("---")
    
    # Escanear la carpeta pública buscando PDFs
    archivos_disponibles = [f for f in os.listdir(CARPETA_RUTAS) if f.endswith('.pdf')]
    
    if not archivos_disponibles:
        st.warning("⚠️ Aún no se han publicado las rutas de hoy.")
        st.info("Por favor espera a que el coordinador publique la programación.")
        if st.button("🔄 Consultar de nuevo"):
            st.rerun()
    else:
        # Procesar nombres para mostrar limpio (Ruta_JUAN.pdf -> JUAN)
        # Creamos un diccionario { "JUAN": "Ruta_JUAN.pdf" }
        opciones_tecnicos = {}
        for archivo in archivos_disponibles:
            nombre_limpio = archivo.replace("Ruta_", "").replace(".pdf", "").replace("_", " ")
            opciones_tecnicos[nombre_limpio] = archivo
            
        nombres_ordenados = sorted(list(opciones_tecnicos.keys()))
        
        # SELECTOR DE NOMBRE
        col_sel, col_info = st.columns([2, 1])
        with col_sel:
            seleccion = st.selectbox("👇 BUSCA TU NOMBRE AQUÍ:", ["-- Seleccionar --"] + nombres_ordenados)
        
        # BOTÓN DE DESCARGA
        if seleccion != "-- Seleccionar --":
            archivo_real = opciones_tecnicos[seleccion]
            ruta_completa = os.path.join(CARPETA_RUTAS, archivo_real)
            
            st.success(f"✅ Ruta encontrada para: **{seleccion}**")
            
            # Leemos el archivo en binario
            with open(ruta_completa, "rb") as file_pdf:
                btn = st.download_button(
                    label=f"📥 DESCARGAR RUTA DE {seleccion}",
                    data=file_pdf,
                    file_name=archivo_real,
                    mime="application/pdf"
                )
            
            st.markdown("---")
            st.caption("ℹ️ Si tienes problemas con la descarga, contacta al coordinador.")

# =============================================================================
# 8. VISTA DEL ADMINISTRADOR (PANEL DE CONTROL)
# =============================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    st.markdown('<div class="titulo-principal">⚙️ Panel de Gestión</div>', unsafe_allow_html=True)
    
    # Login simple
    clave = st.text_input("🔑 Contraseña de acceso:", type="password")
    
    if clave == "ita2026": # CONTRASEÑA
        
        # PESTAÑAS DE GESTIÓN
        tab_base, tab_proceso, tab_publicar = st.tabs([
            "1. Base Operarios", 
            "2. Carga y Balanceo", 
            "3. Publicar Web"
        ])
        
        # --- PESTAÑA 1: BASE DE OPERARIOS ---
        with tab_base:
            st.header("Actualizar Listado de Técnicos")
            maestro_file = st.file_uploader("Subir archivo de Operarios (Excel/CSV)", type=["xlsx", "csv"])
            
            if maestro_file:
                st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
                st.success(f"✅ Base actualizada con {len(st.session_state['mapa_actual'])} barrios mapeados.")
            
            if st.session_state['mapa_actual']:
                st.info(f"Técnicos activos: {len(set(st.session_state['mapa_actual'].values()))}")
                with st.expander("Ver lista de barrios"):
                    st.write(st.session_state['mapa_actual'])
            else:
                st.warning("⚠️ Debes subir el archivo de operarios primero.")

        # --- PESTAÑA 2: CARGA Y BALANCEO ---
        with tab_proceso:
            st.header("Procesar Archivo de Ruta")
            
            c1, c2 = st.columns(2)
            with c1: 
                excel_ruta = st.file_uploader("Subir Excel de Ruta Diaria", type=["xlsx", "csv"])
            with c2: 
                pdf_polizas = st.file_uploader("Subir PDF de Pólizas (Opcional)", type="pdf")
            
            lista_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            if excel_ruta and lista_tecnicos:
                # Leer Excel
                try:
                    if excel_ruta.name.endswith('.csv'): 
                        df_raw = pd.read_csv(excel_ruta, sep=None, engine='python', encoding='utf-8-sig')
                    else: 
                        df_raw = pd.read_excel(excel_ruta)
                    
                    cols_excel = list(df_raw.columns)
                    
                    # Configuración de Cupos
                    st.divider()
                    st.subheader("Configuración de Cupos")
                    df_topes_init = pd.DataFrame({"Técnico": lista_tecnicos, "Cupo Máximo": [35] * len(lista_tecnicos)})
                    edited_topes = st.data_editor(
                        df_topes_init, 
                        column_config={"Cupo Máximo": st.column_config.NumberColumn(min_value=1, max_value=200)}, 
                        hide_index=True, 
                        use_container_width=True
                    )
                    LIMITES = dict(zip(edited_topes["Técnico"], edited_topes["Cupo Máximo"]))
                    
                    # Mapeo de Columnas
                    st.divider()
                    st.subheader("Mapeo de Columnas del Excel")
                    
                    def idx_match(keywords):
                        for i, col in enumerate(cols_excel):
                            for k in keywords:
                                if k in str(col).upper(): return i
                        return 0

                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        sel_bar = st.selectbox("Columna BARRIO", cols_excel, index=idx_match(['BARRIO', 'SECTOR']))
                        sel_cta = st.selectbox("Columna CUENTA", cols_excel, index=idx_match(['CUENTA', 'POLIZA']))
                    with cc2:
                        sel_dir = st.selectbox("Columna DIRECCIÓN", cols_excel, index=idx_match(['DIRECCION', 'DIR']))
                        sel_med = st.selectbox("Columna MEDIDOR", ["NO TIENE"]+cols_excel, index=idx_match(['MEDIDOR'])+1)
                    with cc3:
                        sel_cli = st.selectbox("Columna CLIENTE", ["NO TIENE"]+cols_excel, index=idx_match(['CLIENTE', 'NOMBRE'])+1)
                    
                    col_map_obj = {
                        'BARRIO': sel_bar, 'DIRECCION': sel_dir, 'CUENTA': sel_cta,
                        'MEDIDOR': sel_med if sel_med != "NO TIENE" else None,
                        'CLIENTE': sel_cli if sel_cli != "NO TIENE" else None
                    }

                    # BOTÓN DE PROCESAR
                    if st.button("🚀 EJECUTAR BALANCEO Y ORDENAMIENTO", type="primary"):
                        with st.spinner("Procesando lógica..."):
                            df = df_raw.copy()
                            
                            # 1. Asignación Ideal (Barrio -> Técnico)
                            df['TECNICO_IDEAL'] = df[sel_bar].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                            df['TECNICO_FINAL'] = df['TECNICO_IDEAL']
                            df['ORIGEN_REAL'] = None
                            
                            # 2. ORDENAMIENTO (Usando tu lógica de Tuplas)
                            df['SORT_DIR'] = df[sel_dir].astype(str).apply(natural_sort_key)
                            df = df.sort_values(by=[sel_bar, 'SORT_DIR'])
                            
                            # 3. Balanceo de Cargas
                            conteo = df['TECNICO_IDEAL'].value_counts()
                            for giver in [t for t in lista_tecnicos if conteo.get(t, 0) > LIMITES.get(t, 35)]:
                                tope = LIMITES.get(giver, 35)
                                rows = df[df['TECNICO_FINAL'] == giver]
                                excedente = len(rows) - tope
                                if excedente > 0:
                                    # Movemos los últimos (que suelen estar al final del barrio)
                                    idx_move = rows.index[-excedente:]
                                    counts_now = df['TECNICO_FINAL'].value_counts()
                                    # Buscar el candidato con menos carga
                                    best_cand = sorted([t for t in lista_tecnicos if t != giver], key=lambda x: counts_now.get(x, 0))[0]
                                    df.loc[idx_move, 'TECNICO_FINAL'] = best_cand
                                    df.loc[idx_move, 'ORIGEN_REAL'] = giver
                            
                            # Guardar en sesión
                            st.session_state['df_simulado'] = df.drop(columns=['SORT_DIR'])
                            st.session_state['col_map_final'] = col_map_obj
                            st.success("✅ Ruta procesada y balanceada correctamente.")
                            
                except Exception as e:
                    st.error(f"Error procesando el archivo: {e}")

        # --- PESTAÑA 3: PUBLICACIÓN WEB ---
        with tab_publicar:
            st.header("Publicar Rutas para Descarga")
            
            if st.session_state['df_simulado'] is not None:
                df_final = st.session_state['df_simulado']
                col_map_final = st.session_state['col_map_final']
                
                # Estadísticas previas
                tecnicos_con_ruta = [t for t in df_final['TECNICO_FINAL'].unique() if "SIN_" not in t]
                st.metric("Técnicos con Ruta", len(tecnicos_con_ruta))
                st.metric("Total Visitas", len(df_final))
                
                st.markdown("### ⚠️ Atención")
                st.warning("Al presionar el botón, se borrarán las rutas de ayer y se publicarán las nuevas en el portal.")
                
                if st.button("🌍 PUBLICAR EN EL PORTAL WEB", type="primary"):
                    # 1. Limpiar carpeta
                    limpiar_carpeta_publica()
                    
                    progreso = st.progress(0)
                    estado = st.empty()
                    
                    # 2. Generar PDFs uno por uno
                    count = 0
                    for i, tec in enumerate(tecnicos_con_ruta):
                        estado.text(f"Generando PDF para {tec}...")
                        
                        # Filtrar datos del técnico
                        df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                        
                        # RE-ORDENAMIENTO ASEGURADO (Para el PDF individual)
                        df_t['SORT_TEMP'] = df_t[col_map_final['DIRECCION']].astype(str).apply(natural_sort_key)
                        df_t = df_t.sort_values(by=[col_map_final['BARRIO'], 'SORT_TEMP']).drop(columns=['SORT_TEMP'])
                        
                        # Crear PDF en bytes
                        pdf_bytes = crear_pdf_lista(df_t, tec, col_map_final)
                        
                        # Guardar en disco (Carpeta Pública)
                        nombre_seguro = str(tec).replace(" ", "_").upper()
                        ruta_archivo = os.path.join(CARPETA_RUTAS, f"Ruta_{nombre_seguro}.pdf")
                        
                        with open(ruta_archivo, "wb") as f:
                            f.write(pdf_bytes)
                        
                        count += 1
                        progreso.progress((i + 1) / len(tecnicos_con_ruta))
                    
                    estado.empty()
                    st.balloons()
                    st.success(f"✅ ¡ÉXITO! {count} rutas han sido publicadas.")
                    
                    # GENERAR ZIP OPCIONAL PARA ADMIN
                    st.divider()
                    st.write("Si necesitas descargar TODO en un ZIP para respaldo:")
                    
                    # Lógica del ZIP (Tal cual tu código original)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        # Excel consolidado
                        out_b = io.BytesIO()
                        with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df_final.to_excel(w, index=False)
                        zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", out_b.getvalue())
                        
                        # PDFs individuales
                        for tec in tecnicos_con_ruta:
                            nombre_seguro = str(tec).replace(" ", "_")
                            # Reutilizamos la lógica de generación
                            df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                            df_t['SORT'] = df_t[col_map_final['DIRECCION']].astype(str).apply(natural_sort_key)
                            df_t = df_t.sort_values(by=[col_map_final['BARRIO'], 'SORT']).drop(columns=['SORT'])
                            pdf_bytes = crear_pdf_lista(df_t, tec, col_map_final)
                            zf.writestr(f"{nombre_seguro}/1_HOJA_DE_RUTA.pdf", pdf_bytes)
                    
                    st.download_button(
                        "⬇️ DESCARGAR RESPALDO ZIP COMPLETO",
                        data=zip_buffer.getvalue(),
                        file_name="Respaldo_Rutas_Completo.zip",
                        mime="application/zip"
                    )

            else:
                st.info("Primero debes procesar el archivo en la pestaña 'Carga y Balanceo'.")

    elif clave:
        st.error("❌ Contraseña incorrecta")

# =============================================================================
# FIN DEL CÓDIGO
# =============================================================================
