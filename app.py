#########################################################################################
#                                                                                       #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA - VERSIÓN 9.0 "FORTRESS"                       #
#   AUTOR: YEFREY                                                                       #
#   FECHA: FEBRERO 2026                                                                 #
#                                                                                       #
#   ---------------------------------------------------------------------------------   #
#   RESUMEN DE SEGURIDAD Y FUNCIONALIDAD:                                               #
#   1.  AUTENTICACIÓN DE SESIÓN REAL: El panel lateral de "Asistencia" está oculto      #
#       hasta que la contraseña (ita2026) sea validada correctamente.                   #
#   2.  CORE LOGÍSTICO COMPLETO: Carga, Balanceo, Ajuste Manual y Publicación.          #
#   3.  GENERACIÓN DOCUMENTAL ROBUSTA: ZIP con estructura de carpetas y PDF.            #
#   4.  INTERFAZ DE USUARIO: Diseño "Diamond" mantenido y mejorado.                     #
#   5.  SIN RECORTES: Lógica expandida para máxima trazabilidad de errores.             #
#                                                                                       #
#########################################################################################

import streamlit as st
import fitz  # PyMuPDF: Motor de procesamiento de PDFs
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
import base64

# =======================================================================================
# SECCIÓN 1: CONFIGURACIÓN VISUAL, ESTILOS Y SESIÓN
# =======================================================================================

# Configuración inicial de la página
st.set_page_config(
    page_title="Logística ITA | Fortress v9.0",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema Logístico ITA - Versión 9.0 Segura"
    }
)

# Inicialización de Variables de Sesión (Estado Global)
# Esto es vital para recordar si el usuario ya puso la contraseña correcta.
if 'admin_logged_in' not in st.session_state: st.session_state['admin_logged_in'] = False
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'tecnicos_activos_manual' not in st.session_state: st.session_state['tecnicos_activos_manual'] = []

# Inyección de CSS (Estilos Avanzados)
st.markdown("""
    <style>
    /* FUENTES Y COLORES GLOBALES */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
    
    .stApp { 
        background-color: #0B1120; /* Dark Slate */
        color: #F8FAFC; 
        font-family: 'Roboto', sans-serif;
    }
    
    /* SIDEBAR BLINDADA */
    section[data-testid="stSidebar"] {
        background-color: #111827; 
        border-right: 1px solid #1E293B;
    }
    
    /* CONTENEDOR DE LOGO */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 25px;
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .logo-img {
        width: 90px;
        height: auto;
        filter: drop-shadow(0 0 15px rgba(56, 189, 248, 0.6));
        transition: transform 0.3s ease;
    }
    .logo-img:hover {
        transform: scale(1.05);
    }
    
    .logo-text {
        font-family: 'Roboto', sans-serif;
        font-weight: 900;
        font-size: 26px;
        background: -webkit-linear-gradient(45deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 10px;
        letter-spacing: 1.5px;
    }
    
    /* PESTAÑAS PERSONALIZADAS */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        background-color: #1F2937;
        padding: 10px 10px 0 10px;
        border-radius: 12px 12px 0 0;
        border-bottom: 1px solid #374151;
    }
    .stTabs [data-baseweb="tab"] { 
        height: 55px; 
        background-color: transparent; 
        color: #94A3B8; 
        border: none;
        font-weight: 600;
        font-size: 15px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border-radius: 8px 8px 0 0;
    }
    
    /* INPUTS Y SELECTBOXES */
    div[data-baseweb="select"] > div {
        background-color: #1F2937;
        color: white;
        border-color: #374151;
        border-radius: 8px;
    }
    
    /* BOTONES PRIMARIOS (AZUL) */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
        color: white; 
        border-radius: 10px; 
        height: 52px; 
        width: 100%; 
        font-size: 16px; 
        font-weight: 700; 
        border: 1px solid #1D4ED8;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        box-shadow: 0 8px 15px rgba(37, 99, 235, 0.4);
        transform: translateY(-1px);
    }
    
    /* BOTONES DE DESCARGA (VERDE) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        color: white; 
        border-radius: 10px; 
        height: 58px; 
        width: 100%; 
        font-size: 17px; 
        font-weight: 700; 
        border: 1px solid #059669;
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }

    /* MENSAJES DE ALERTA */
    .locked-msg {
        background-color: #450a0a;
        color: #fecaca;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #7f1d1d;
        text-align: center;
        font-weight: bold;
    }
    
    .unlocked-msg {
        background-color: #064e3b;
        color: #a7f3d0;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #065f46;
        text-align: center;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =======================================================================================
# SECCIÓN 2: GESTIÓN DE SISTEMA DE ARCHIVOS (PERSISTENCIA WEB)
# =======================================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_sistema_archivos(accion="iniciar"):
    """
    Función de bajo nivel para administrar la carpeta de archivos públicos.
    Maneja excepciones de bloqueo de archivos y reintentos.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
            except OSError as e:
                st.error(f"Error inicializando sistema de archivos: {e}")
                
    elif accion == "limpiar":
        # Intento de borrado seguro
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.2) # Pausa para el sistema operativo
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                # Si falla borrar la raíz, borramos contenido interno
                try:
                    for filename in os.listdir(CARPETA_PUBLICA):
                        file_path = os.path.join(CARPETA_PUBLICA, filename)
                        if os.path.isfile(file_path): os.unlink(file_path)
                        elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except:
                    pass # Fallo silencioso no crítico
        else:
            os.makedirs(CARPETA_PUBLICA)

# Inicializamos el sistema de archivos al cargar el script
gestionar_sistema_archivos("iniciar")

# =======================================================================================
# SECCIÓN 3: FUNCIONES DE NORMALIZACIÓN Y LÓGICA CORE
# =======================================================================================

def limpiar_estricto(txt):
    """
    Normalización de texto de alta precisión.
    Elimina tildes, caracteres especiales y espacios redundantes.
    """
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """
    Limpia números de identificación (Cuentas, Pólizas, Celulares).
    Corrige el formato float de Excel (ej: 300123.0 -> 300123).
    """
    if not txt: return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): 
        txt_str = txt_str[:-2]
    # Eliminar cualquier caracter no numérico
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """
    Clave de ordenamiento natural.
    Permite ordenar direcciones lógicamente (Calle 2, Calle 10, Calle 20).
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Algoritmo de búsqueda de asignación.
    Prioriza exactitud, luego flexibilidad, luego contención segura.
    """
    if not barrio_input: return "SIN_ASIGNAR"
    
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    # 1. Coincidencia Exacta
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 2. Coincidencia Flexible (Eliminando palabras comunes)
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL|CONJUNTO)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 3. Coincidencia Parcial (Contención) - Longitud mínima 4 para evitar falsos positivos
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: 
            return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Carga el archivo maestro de operarios.
    Detecta automáticamente las columnas de Barrio y Técnico.
    """
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        if len(df.columns) < 2: return {}
            
        c_barrio = df.columns[0]
        c_tecnico = df.columns[1]

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_barrio]))
            t = str(row[c_tecnico]).upper().strip()
            
            if t and t != "NAN" and b: 
                mapa[b] = t
                
    except Exception as e:
        st.error(f"Error leyendo maestro: {str(e)}")
        return {}
        
    return mapa

def procesar_pdf_polizas_avanzado(file_obj):
    """
    Motor de escaneo de PDFs.
    Extrae páginas individuales por número de póliza/cuenta.
    Detecta anexos en páginas subsiguientes.
    """
    file_obj.seek(0)
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    diccionario_extraido = {}
    
    total_paginas = len(doc)
    
    for i in range(total_paginas):
        texto_pagina = doc[i].get_text()
        # Regex robusta para encontrar patrones de cuenta/poliza
        matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pagina, re.IGNORECASE)
        
        if matches:
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            
            # Verificar si la siguiente página es un anexo (no tiene título de póliza)
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
            
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            
            for m in matches:
                diccionario_extraido[normalizar_numero(m)] = pdf_bytes
                
    return diccionario_extraido

# =======================================================================================
# SECCIÓN 4: GENERACIÓN DE DOCUMENTOS PDF (FPDF)
# =======================================================================================

class PDFListado(FPDF):
    def header(self):
        # Fondo Azul Institucional
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        
        # Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Datos Generales
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    # Encabezados
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Datos
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # Color Rojo para Apoyos
        barrio_txt = str(row[col_map['BARRIO']])
        if pd.notna(row.get('ORIGEN_REAL')):
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0) # Rojo
        else:
            pdf.set_text_color(0, 0, 0)

        def get_s(k):
            c = col_map.get(k)
            return str(row[c]) if c and c != "NO TIENE" else ""

        row_data = [
            str(idx), 
            get_s('CUENTA'), 
            get_s('MEDIDOR')[:15], 
            barrio_txt[:38], 
            get_s('DIRECCION')[:60], 
            get_s('CLIENTE')[:30]
        ]
        
        for val, w in zip(row_data, widths):
            try: val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# =======================================================================================
# SECCIÓN 5: BARRA LATERAL INTELIGENTE Y SEGURA
# =======================================================================================

with st.sidebar:
    # 1. IDENTIDAD CORPORATIVA
    st.markdown("""
        <div class="logo-container">
            <img src="https://cdn-icons-png.flaticon.com/512/2942/2942813.png" class="logo-img">
            <p class="logo-text">ITA RADIAN</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. SELECTOR DE ROL DE ACCESO
    modo_acceso = st.selectbox(
        "SELECCIONA TU PERFIL", 
        ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0 # Por defecto Técnico
    )
    
    st.markdown("---")
    
    # 3. CONTROL DE ASISTENCIA BLINDADO
    # Lógica de Seguridad:
    # A) Debe ser Administrador.
    # B) Debe estar Logueado (admin_logged_in = True).
    # C) Debe haber cargado la base de datos (mapa_actual).
    
    if modo_acceso == "⚙️ ADMINISTRADOR":
        if st.session_state.get('admin_logged_in', False):
            # Usuario autenticado correctamente
            if st.session_state['mapa_actual']:
                st.markdown("### 📋 Gestión de Asistencia")
                st.info("Desmarca a los técnicos ausentes para redistribuir su carga.")
                
                # Obtener lista completa
                todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
                
                # Widget de Asistencia
                seleccion_activos = st.multiselect(
                    "Técnicos Habilitados:",
                    options=todos_tecnicos,
                    default=todos_tecnicos,
                    key="asistencia_sidebar"
                )
                
                # Persistencia
                st.session_state['tecnicos_activos_manual'] = seleccion_activos
                
                # Feedback Visual
                inactivos = len(todos_tecnicos) - len(seleccion_activos)
                if inactivos > 0:
                    st.error(f"🔴 {inactivos} Técnicos INACTIVOS")
                else:
                    st.success("🟢 Asistencia Completa")
            else:
                st.caption("ℹ️ Carga el Maestro en Pestaña 1 para ver la lista aquí.")
        else:
            # Mensaje cuando no ha iniciado sesión
            st.markdown("""
                <div class="locked-msg">
                    🔒 MENÚ BLOQUEADO<br>
                    Inicia sesión para ver controles.
                </div>
            """, unsafe_allow_html=True)

    elif modo_acceso == "👷 TÉCNICO":
        st.info("Bienvenido al Portal de Autogestión v9.0")

    st.markdown("---")
    st.caption("Sistema Logístico Seguro v9.0")

# =======================================================================================
# SECCIÓN 6: VISTA DEL TÉCNICO (PORTAL DE DESCARGAS)
# =======================================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown("""
        <h1 style='text-align: center; color: #34D399; margin-bottom: 0;'>🚛 ZONA DE DESCARGAS</h1>
        <p style='text-align: center; color: #94A3B8; margin-top: 5px;'>Portal de Autogestión de Documentos Operativos</p>
        <hr style='border-color: #334155;'>
    """, unsafe_allow_html=True)
    
    # Verificar archivos publicados
    tecnicos_list = []
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    
    if not tecnicos_list:
        col_c = st.columns([1, 2, 1])
        with col_c[1]:
            st.warning("⏳ Las rutas del día aún no están disponibles.")
            if st.button("🔄 Consultar Nuevamente", type="secondary"): st.rerun()
    else:
        # Selector Centralizado
        col_espacio1, col_centro, col_espacio2 = st.columns([1, 2, 1])
        with col_centro:
            seleccion = st.selectbox("👇 SELECCIONA TU NOMBRE:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            path_tec = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(path_tec, "1_HOJA_DE_RUTA.pdf")
            f_leg = os.path.join(path_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"<h3 style='text-align:center; color:white; margin-top:20px;'>Documentos para: <span style='color:#38BDF8'>{seleccion}</span></h3>", unsafe_allow_html=True)
            st.write("")
            
            c_izq, c_der = st.columns(2)
            
            with c_izq:
                st.markdown("""
                <div style='background:#1E293B; padding:20px; border-radius:10px; border-left:5px solid #38BDF8;'>
                    <h4 style='color:#38BDF8; margin:0;'>📄 1. Hoja de Ruta</h4>
                    <p style='color:#94A3B8; margin:5px 0 0 0;'>Listado de visitas y clientes.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f:
                        st.download_button("⬇️ DESCARGAR RUTA", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="d_ruta", use_container_width=True)
                else: st.error("No disponible")
                
            with c_der:
                st.markdown("""
                <div style='background:#1E293B; padding:20px; border-radius:10px; border-left:5px solid #34D399;'>
                    <h4 style='color:#34D399; margin:0;'>📂 2. Legalización</h4>
                    <p style='color:#94A3B8; margin:5px 0 0 0;'>Paquete de Pólizas.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f:
                        st.download_button("⬇️ DESCARGAR PAQUETE", f, f"Leg_{seleccion}.pdf", "application/pdf", key="d_leg", use_container_width=True)
                else: st.info("Hoy no tienes pólizas.")

# =======================================================================================
# SECCIÓN 7: VISTA DEL ADMINISTRADOR (PANEL DE GESTIÓN)
# =======================================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    
    # -----------------------------------------------------------
    # FASE 1: AUTENTICACIÓN (Login Gate)
    # -----------------------------------------------------------
    if not st.session_state.get('admin_logged_in', False):
        col_login_spacer1, col_login, col_login_spacer2 = st.columns([1, 1, 1])
        
        with col_login:
            st.markdown("<h2 style='text-align: center;'>🔐 Acceso Administrativo</h2>", unsafe_allow_html=True)
            password = st.text_input("Contraseña:", type="password", placeholder="Ingresa tu clave aquí...")
            
            if st.button("INGRESAR AL SISTEMA", type="primary"):
                if password == "ita2026":
                    st.session_state['admin_logged_in'] = True
                    st.success("✅ Acceso Concedido")
                    st.rerun()
                else:
                    st.error("❌ Contraseña Incorrecta")
                    
    # -----------------------------------------------------------
    # FASE 2: PANEL DE CONTROL (Solo si está logueado)
    # -----------------------------------------------------------
    else:
        # Header con botón de Logout
        col_tit, col_logout = st.columns([4, 1])
        with col_tit:
            st.markdown("## ⚙️ Panel Maestro de Logística")
        with col_logout:
            if st.button("Cerrar Sesión"):
                st.session_state['admin_logged_in'] = False
                st.rerun()
        
        # Tabs de Gestión
        tab1, tab2, tab3, tab4 = st.tabs([
            "1. 🗃️ Base Operarios", 
            "2. ⚖️ Carga & Balanceo", 
            "3. 🛠️ Ajuste Manual", 
            "4. 🌍 Publicación Final"
        ])
        
        # --- TAB 1: CARGA DE MAESTRO ---
        with tab1:
            st.markdown("### Configuración de Zonas y Técnicos")
            st.info("Carga aquí el archivo que relaciona cada Barrio con su Técnico responsable.")
            
            f_maestro = st.file_uploader("Subir Maestro (Excel/CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                with st.spinner("Indexando base de datos..."):
                    st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
                
                if st.session_state['mapa_actual']:
                    st.success(f"✅ Maestro cargado con éxito: {len(st.session_state['mapa_actual'])} barrios indexados.")
                    st.markdown("""
                        <div class='unlocked-msg'>
                            🔓 <b>MENÚ DE ASISTENCIA DESBLOQUEADO</b><br>
                            Revisa la barra lateral izquierda para inactivar técnicos.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ Error en el archivo: Verifica columnas 'Barrio' y 'Tecnico'.")

        # --- TAB 2: PROCESO DIARIO ---
        with tab2:
            st.markdown("### Carga de Insumos del Día")
            
            c_pdf, c_xls = st.columns(2)
            with c_pdf:
                st.markdown("**1. Pólizas (PDF)**")
                up_pdf = st.file_uploader("Archivo PDF Pólizas", type="pdf")
                if up_pdf and st.button("Escanear PDF"):
                    with st.spinner("Procesando..."):
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                        st.success(f"✅ {len(st.session_state['mapa_polizas_cargado'])} Pólizas extraídas.")

            with c_xls:
                st.markdown("**2. Ruta (Excel)**")
                up_xls = st.file_uploader("Archivo Excel Ruta", type=["xlsx", "csv"])
            
            # Determinar Técnicos Activos (Respetando Asistencia)
            if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                tecnicos_hoy = st.session_state['tecnicos_activos_manual']
            elif st.session_state['mapa_actual']:
                tecnicos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))
            else:
                tecnicos_hoy = []

            if up_xls and tecnicos_hoy:
                if up_xls.name.endswith('.csv'): df = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(up_xls)
                cols = list(df.columns)
                
                st.divider()
                st.markdown("#### Parámetros de Balanceo")
                
                # Configuración Cupos
                df_cup = pd.DataFrame({"Técnico": tecnicos_hoy, "Cupo": [35]*len(tecnicos_hoy)})
                ed_cup = st.data_editor(df_cup, column_config={"Cupo": st.column_config.NumberColumn(min_value=1)}, hide_index=True, use_container_width=True)
                LIMITES = dict(zip(ed_cup["Técnico"], ed_cup["Cupo"]))
                
                # Configuración Mapeo
                def ix(k): 
                    for i,c in enumerate(cols): 
                        for x in k: 
                            if x in str(c).upper(): return i
                    return 0
                
                c1, c2, c3 = st.columns(3)
                sb = c1.selectbox("Barrio", cols, index=ix(['BARRIO']))
                sd = c2.selectbox("Dirección", cols, index=ix(['DIR','DIRECCION']))
                sc = c3.selectbox("Cuenta", cols, index=ix(['CUENTA']))
                sm = st.selectbox("Medidor", ["NO TIENE"]+cols, index=ix(['MEDIDOR'])+1)
                sl = st.selectbox("Cliente", ["NO TIENE"]+cols, index=ix(['CLIENTE'])+1)
                cmap = {'BARRIO': sb, 'DIRECCION': sd, 'CUENTA': sc, 'MEDIDOR': sm if sm!="NO TIENE" else None, 'CLIENTE': sl if sl!="NO TIENE" else None}
                
                if st.button("🚀 EJECUTAR BALANCEO AUTOMÁTICO", type="primary"):
                    # Auto-scan
                    if up_pdf and not st.session_state['mapa_polizas_cargado']:
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                    
                    df_proc = df.copy()
                    
                    # 1. Asignar Ideal
                    df_proc['TECNICO_IDEAL'] = df_proc[sb].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                    
                    # 2. Manejo de Inactivos
                    df_proc['TECNICO_FINAL'] = df_proc['TECNICO_IDEAL'].apply(lambda x: x if x in tecnicos_hoy else "VACANTE")
                    df_proc['ORIGEN_REAL'] = None
                    
                    # Marcar vacantes
                    msk_vac = df_proc['TECNICO_FINAL'] == "VACANTE"
                    df_proc.loc[msk_vac, 'ORIGEN_REAL'] = df_proc.loc[msk_vac, 'TECNICO_IDEAL']
                    
                    # 3. Ordenar
                    df_proc['S'] = df_proc[sd].astype(str).apply(natural_sort_key)
                    df_proc = df_proc.sort_values(by=[sb, 'S'])
                    
                    # 4. Repartir Vacantes
                    vacs = df_proc[df_proc['TECNICO_FINAL'] == "VACANTE"]
                    for idx_v, _ in vacs.iterrows():
                        cnt_live = df_proc[df_proc['TECNICO_FINAL'].isin(tecnicos_hoy)]['TECNICO_FINAL'].value_counts()
                        for t in tecnicos_hoy:
                            if t not in cnt_live: cnt_live[t] = 0
                        mejor = cnt_live.idxmin()
                        df_proc.at[idx_v, 'TECNICO_FINAL'] = mejor
                    
                    # 5. Balancear Cupos
                    cnt = df_proc['TECNICO_FINAL'].value_counts()
                    for tech in [t for t in tecnicos_hoy if cnt.get(t,0) > LIMITES.get(t,35)]:
                        tope = LIMITES.get(tech, 35)
                        rows = df_proc[df_proc['TECNICO_FINAL'] == tech]
                        exc = len(rows) - tope
                        
                        if exc > 0:
                            mov = rows.index[-exc:]
                            now = df_proc['TECNICO_FINAL'].value_counts()
                            for t in tecnicos_hoy: 
                                if t not in now: now[t]=0
                            best = sorted([t for t in tecnicos_hoy if t!=tech], key=lambda x: now.get(x,0))[0]
                            df_proc.loc[mov, 'TECNICO_FINAL'] = best
                            df_proc.loc[mov, 'ORIGEN_REAL'] = tech
                    
                    st.session_state['df_simulado'] = df_proc.drop(columns=['S'])
                    st.session_state['col_map_final'] = cmap
                    st.success("✅ Balanceo completado.")

            elif not tecnicos_hoy and st.session_state['mapa_actual']:
                st.error("⚠️ No hay técnicos activos. Revisa la barra lateral.")

        # --- TAB 3: AJUSTE MANUAL ---
        with tab3:
            st.markdown("### 🛠️ Corrección Fina")
            if st.session_state['df_simulado'] is not None:
                df = st.session_state['df_simulado']
                cbar = st.session_state['col_map_final']['BARRIO']
                activos_con_carga = sorted(df['TECNICO_FINAL'].unique())
                
                destinos_posibles = st.session_state.get('tecnicos_activos_manual', [])

                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
                with c1: org = st.selectbox("De:", ["-"]+list(activos_con_carga))
                with c2: 
                    if org!="-":
                        brs = df[df['TECNICO_FINAL']==org][cbar].value_counts()
                        bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in brs.items()])
                    else: bar=None
                with c3: dst = st.selectbox("Para:", ["-"]+destinos_posibles)
                with c4:
                    st.write("")
                    if st.button("Mover Barrio"):
                        if bar and dst!="-":
                            rb = bar.rsplit(" (",1)[0]
                            msk = (df['TECNICO_FINAL']==org) & (df[cbar]==rb)
                            df.loc[msk, 'TECNICO_FINAL'] = dst
                            df.loc[msk, 'ORIGEN_REAL'] = org
                            st.session_state['df_simulado'] = df; st.rerun()
                
                cls = st.columns(2)
                for i, t in enumerate(activos_con_carga):
                    with cls[i%2]:
                        s = df[df['TECNICO_FINAL']==t]
                        r = s.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='N')
                        r['B'] = r.apply(lambda x: f"⚠️ {x[cbar]}" if pd.notna(x['ORIGEN_REAL']) else x[cbar], axis=1)
                        with st.expander(f"👷 {t} ({len(s)})"): st.dataframe(r[['B','N']], hide_index=True, use_container_width=True)
            else: st.info("Sin datos.")

        # --- TAB 4: PUBLICAR ---
        with tab4:
            st.markdown("### 🌍 Distribución")
            if st.session_state['df_simulado'] is not None:
                dff = st.session_state['df_simulado']
                cmf = st.session_state['col_map_final']
                pls = st.session_state['mapa_polizas_cargado']
                tfin = [t for t in dff['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                if st.button("📢 PUBLICAR EN PORTAL WEB", type="primary"):
                    gestionar_sistema_archivos("limpiar")
                    pg = st.progress(0)
                    for i, t in enumerate(tfin):
                        dt = dff[dff['TECNICO_FINAL']==t].copy()
                        dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                        dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                        
                        safe = str(t).replace(" ","_")
                        pto = os.path.join(CARPETA_PUBLICA, safe); os.makedirs(pto, exist_ok=True)
                        
                        # Ruta
                        with open(os.path.join(pto, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(crear_pdf_lista_final(dt, t, cmf))
                        
                        # Legalizacion
                        if pls:
                            mg = fitz.open(); n=0
                            for _,r in dt.iterrows():
                                c = normalizar_numero(str(r[cmf['CUENTA']]))
                                if c in pls:
                                    with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                    n+=1
                            if n>0:
                                with open(os.path.join(pto, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f: f.write(mg.tobytes())
                            mg.close()
                        pg.progress((i+1)/len(tfin))
                    st.success("✅ Rutas Publicadas en Web.")
                    st.balloons()
                
                st.divider()
                st.markdown("#### 📦 Descargas Administrativas")
                
                if st.button("GENERAR ZIP MAESTRO COMPLETO"):
                    bf = io.BytesIO()
                    with zipfile.ZipFile(bf,"w") as z:
                        # 0. Banco
                        if pls:
                            for k,v in pls.items(): z.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                        
                        # 0. Excel
                        out = io.BytesIO(); 
                        with pd.ExcelWriter(out, engine='xlsxwriter') as w: dff.to_excel(w, index=False)
                        z.writestr("00_CONSOLIDADO.xlsx", out.getvalue())
                        
                        # Carpetas
                        for t in tfin:
                            safe = str(t).replace(" ","_")
                            dt = dff[dff['TECNICO_FINAL']==t].copy()
                            dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                            dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                            
                            # 1. Hoja
                            z.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(dt, t, cmf))
                            
                            # 2. Tabla
                            ot = io.BytesIO()
                            with pd.ExcelWriter(ot, engine='xlsxwriter') as w: dt.to_excel(w, index=False)
                            z.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", ot.getvalue())
                            
                            # 3 y 4. Polizas
                            if pls:
                                mg = fitz.open(); n=0
                                for _,r in dt.iterrows():
                                    c = normalizar_numero(str(r[cmf['CUENTA']]))
                                    if c in pls:
                                        # Carpeta 4: Individuales
                                        z.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{c}.pdf", pls[c])
                                        # Carpeta 3: Merge
                                        with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                        n+=1
                                if n>0: z.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", mg.tobytes())
                                mg.close()
                                
                    st.session_state['zip_admin_ready'] = bf.getvalue()
                    st.success("ZIP Creado.")
                
                if st.session_state['zip_admin_ready']:
                    st.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

            else: st.info("Pendiente procesar ruta.")
