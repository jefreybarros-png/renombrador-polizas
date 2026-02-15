#################################################################################
#                                                                               #
#   SISTEMA DE GESTIÓN LOGÍSTICA ITA - PLATAFORMA INTEGRAL (WEB + ADMIN)        #
#   VERSIÓN: 5.0 ULTIMATE (BLINDADA)                                            #
#   AUTOR: YEFREY                                                               #
#   FECHA ACTUALIZACIÓN: FEBRERO 2026                                           #
#                                                                               #
#   DESCRIPCIÓN TÉCNICA:                                                        #
#   Este sistema es un monolito que integra:                                    #
#   1.  Motor de Lectura de PDFs (PyMuPDF) para extracción de pólizas.          #
#   2.  Motor de Procesamiento de Datos (Pandas) para balanceo de cargas.       #
#   3.  Algoritmo de Ordenamiento Natural (Natural Sort) para direcciones.      #
#   4.  Interfaz de Ajuste Manual para reasignación de zonas/barrios.           #
#   5.  Sistema de Archivos Local para persistencia temporal (Publicación Web). #
#   6.  Generador de ZIP Estructurado para respaldo administrativo.             #
#                                                                               #
#################################################################################

import streamlit as st
import fitz  # Librería PyMuPDF para manipulación de PDFs
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

# ===============================================================================
# SECCIÓN 1: CONFIGURACIÓN GLOBAL DE LA APLICACIÓN
# ===============================================================================

# Configuración de la página del navegador
st.set_page_config(
    page_title="Logística ITA V5.0",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema Logístico ITA - Versión 5.0 Ultimate"
    }
)

# Inyección de CSS Avanzado para mejorar la interfaz de usuario (UI/UX)
st.markdown("""
    <style>
    /* 1. Fondo y Tipografía Global */
    .stApp { 
        background-color: #0E1117; 
        color: #FAFAFA; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 2. Personalización de las Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 10px; 
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] { 
        height: 60px; 
        background-color: #1F2937; 
        color: #E5E7EB; 
        border-radius: 8px; 
        border: 1px solid #374151; 
        font-weight: 600;
        font-size: 16px;
        padding: 0 20px;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border: 2px solid #60A5FA; 
        box-shadow: 0 0 10px rgba(37, 99, 235, 0.5);
    }
    
    /* 3. Estilos para Tablas y Dataframes */
    div[data-testid="stDataFrame"] { 
        background-color: #262730; 
        border-radius: 12px; 
        padding: 15px;
        border: 1px solid #374151;
    }
    
    /* 4. Botones de Acción Primaria (Azules - Procesos) */
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
        color: white; 
        border-radius: 10px; 
        height: 55px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: bold; 
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: transform 0.1s, box-shadow 0.1s;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(90deg, #3B82F6 0%, #2563EB 100%);
        box-shadow: 0 6px 8px rgba(0,0,0,0.4);
    }
    div.stButton > button:first-child:active {
        transform: translateY(2px);
    }
    
    /* 5. Botones de Descarga (Verdes - Archivos) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(90deg, #059669 0%, #047857 100%);
        color: white; 
        border-radius: 10px; 
        height: 65px; 
        width: 100%; 
        font-size: 20px; 
        font-weight: bold; 
        border: 1px solid #34D399;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(90deg, #10B981 0%, #059669 100%);
    }

    /* 6. Encabezados Especiales para el Portal Técnico */
    .header-tecnico {
        font-size: 36px; 
        font-weight: 900; 
        background: -webkit-linear-gradient(#34D399, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 25px; 
        border-bottom: 3px solid #34D399; 
        padding-bottom: 15px;
    }
    
    .status-card {
        padding: 20px; 
        border-radius: 12px; 
        background-color: #1F2937;
        border-left: 6px solid #2563EB; 
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .status-card h4 { margin: 0; color: #60A5FA; }
    .status-card p { margin: 5px 0 0 0; color: #9CA3AF; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# ===============================================================================
# SECCIÓN 2: GESTIÓN DEL SISTEMA DE ARCHIVOS (PERSISTENCIA WEB)
# ===============================================================================

# Definimos la carpeta raíz para los archivos públicos
CARPETA_PUBLICA = "public_files"

def gestionar_carpeta_publica(accion="iniciar"):
    """
    Función robusta para manejar la carpeta de archivos públicos.
    Acciones:
    - 'iniciar': Crea la carpeta si no existe.
    - 'limpiar': Borra todo el contenido de forma segura para reiniciar el día.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
                print(f"Directorio {CARPETA_PUBLICA} creado.")
            except Exception as e:
                st.error(f"Error crítico creando directorio público: {e}")
                
    elif accion == "limpiar":
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                # Pequeña pausa para asegurar que el sistema operativo libere los archivos
                time.sleep(0.2) 
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                st.warning(f"Advertencia al limpiar carpeta (archivos en uso?): {e}")
                # Intentamos recrear por si acaso
                if not os.path.exists(CARPETA_PUBLICA):
                    os.makedirs(CARPETA_PUBLICA)
        else:
            os.makedirs(CARPETA_PUBLICA)

# Inicializamos el sistema de archivos al cargar el script
gestionar_carpeta_publica("iniciar")

# ===============================================================================
# SECCIÓN 3: BIBLIOTECA DE FUNCIONES DE UTILIDAD (TEXTO Y DATOS)
# ===============================================================================

def limpiar_estricto(txt):
    """
    Normaliza cadenas de texto para comparaciones exactas.
    1. Convierte a mayúsculas.
    2. Elimina espacios al inicio y final.
    3. Elimina tildes y diacríticos (Á -> A, ñ -> n).
    """
    if not txt: return ""
    txt = str(txt).upper().strip()
    # Descomposición Unicode para separar caracteres base de sus acentos
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """
    Limpia cadenas que deberían ser numéricas (Cuentas, Pólizas).
    Elimina caracteres no numéricos y corrige el error de punto flotante de Excel.
    Ejemplo: '12345.0' -> '12345'
    """
    if not txt: return ""
    txt_str = str(txt)
    # Corrección específica para floats de Excel
    if txt_str.endswith('.0'): 
        txt_str = txt_str[:-2]
    # Regex para dejar solo dígitos 0-9
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """
    Algoritmo de Ordenamiento Natural.
    Permite que 'Calle 2' se ordene antes que 'Calle 10'.
    Devuelve una tupla de (int, str) bloques para que Python ordene correctamente.
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    # Divide el texto en partes numéricas y no numéricas
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# ===============================================================================
# SECCIÓN 4: LÓGICA DE NEGOCIO (BUSCADORES Y CARGADORES)
# ===============================================================================

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Algoritmo de búsqueda de técnico responsable por barrio.
    Prioridad:
    1. Coincidencia exacta (limpia).
    2. Coincidencia flexible (sin palabras como 'BARRIO', 'URB').
    3. Coincidencia parcial (substring).
    """
    if not barrio_input: return "SIN_ASIGNAR"
    
    # 1. Limpieza base
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    # 2. Intento Exacto
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 3. Intento Flexible (Quitando prefijos comunes)
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 4. Intento de Contención (Substring) - Con cuidado de no falsos positivos cortos
    for k, v in mapa_barrios.items():
        # Verificamos si el barrio del mapa está dentro del input o viceversa
        # Longitud mínima 4 para evitar que 'SAN' coincida con todo
        if len(k) > 4 and k in b_raw: 
            return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Carga el archivo maestro de operarios.
    Soporta .xlsx y .csv.
    Detecta automáticamente las columnas (Barrio en col 0, Técnico en col 1).
    """
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        # Normalización de cabeceras
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Asunción de estructura: Col 0 = Barrio, Col 1 = Técnico
        if len(df.columns) < 2:
            st.error("El archivo maestro debe tener al menos 2 columnas (Barrio, Técnico).")
            return {}
            
        c_barrio = df.columns[0]
        c_tecnico = df.columns[1]

        count = 0
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_barrio]))
            t = str(row[c_tecnico]).upper().strip()
            
            if t and t != "NAN" and b: 
                mapa[b] = t
                count += 1
                
        # st.write(f"Depuración: Cargados {count} registros del maestro.")
                
    except Exception as e:
        st.error(f"Error crítico leyendo el maestro: {str(e)}")
        return {}
        
    return mapa

def procesar_pdf_polizas_avanzado(file_obj):
    """
    Escanea un PDF multipágina y extrae páginas individuales basadas en números de póliza/cuenta.
    Devuelve un diccionario { 'numero_cuenta': bytes_pdf }.
    """
    file_obj.seek(0) # Reiniciar puntero del archivo
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    diccionario_extraido = {}
    
    total_paginas = len(doc)
    paginas_encontradas = 0
    
    for i in range(total_paginas):
        texto_pagina = doc[i].get_text()
        
        # Regex poderosa para encontrar patrones de cuenta/poliza
        # Busca palabras clave seguidas de números de 4 a 15 dígitos
        matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pagina, re.IGNORECASE)
        
        if matches:
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            
            # Lógica de ANEXOS:
            # Si la siguiente página NO tiene un número de póliza, asumimos que es continuación de esta.
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
            
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            
            # Guardamos la referencia para cada número encontrado en la página
            for m in matches:
                num_limpio = normalizar_numero(m)
                diccionario_extraido[num_limpio] = pdf_bytes
                paginas_encontradas += 1
                
    return diccionario_extraido

# ===============================================================================
# SECCIÓN 5: GENERADOR DE REPORTES PDF (FPDF)
# ===============================================================================

class PDFListado(FPDF):
    """Clase extendida de FPDF para el formato corporativo de ITA."""
    def header(self):
        # Fondo Azul Institucional
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F') # 297mm es el ancho de A4 Horizontal
        
        # Texto del Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    """
    Genera el binario del PDF de la Hoja de Ruta.
    Maneja colores condicionales para barrios de apoyo.
    """
    # Configuración: A4, Horizontal (Landscape), Milímetros
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Subtítulo Informativo
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    total_items = len(df)
    
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha_actual} | TOTAL VISITAS: {total_items}", 0, 1)
    
    # Definición de Columnas
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60] # Suma total: 270mm (aprox margen A4)
    
    # Renderizado de Cabeceras
    pdf.set_fill_color(220, 220, 220) # Gris claro
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): 
        pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Renderizado de Filas
    pdf.set_font('Arial', '', 8)
    
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # Lógica de Color para Apoyos
        barrio_texto = str(row[col_map['BARRIO']])
        
        if pd.notna(row.get('ORIGEN_REAL')):
            # Es un apoyo -> Texto ROJO y etiqueta
            barrio_texto = f"[APOYO] {barrio_texto}"
            pdf.set_text_color(200, 0, 0)
        else:
            # Es propio -> Texto NEGRO
            pdf.set_text_color(0, 0, 0)
        
        # Función auxiliar segura para obtener datos
        def get_safe(k):
            col = col_map.get(k)
            return str(row[col]) if col and col != "NO TIENE" else ""

        # Datos de la fila
        fila_datos = [
            str(idx), 
            get_safe('CUENTA'), 
            get_safe('MEDIDOR')[:15], # Truncar si es muy largo
            barrio_texto[:38],        # Truncar barrio
            get_safe('DIRECCION')[:60], # Truncar dirección
            get_safe('CLIENTE')[:30]    # Truncar cliente
        ]
        
        # Escribir celdas
        for val, w in zip(fila_datos, widths):
            try: 
                # Codificación Latin-1 para caracteres españoles
                val_encoded = val.encode('latin-1', 'replace').decode('latin-1')
            except: 
                val_encoded = val
            
            pdf.cell(w, 7, val_encoded, 1, 0, 'L')
        pdf.ln()
        
    # Retornar los bytes del PDF
    return pdf.output(dest='S').encode('latin-1')

# ===============================================================================
# SECCIÓN 6: GESTIÓN DE VARIABLES DE SESIÓN (ESTADO PERSISTENTE)
# ===============================================================================

# Inicializamos todas las variables de sesión si no existen
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'zip_polizas_only' not in st.session_state: st.session_state['zip_polizas_only'] = None

# ===============================================================================
# SECCIÓN 7: INTERFAZ DE USUARIO - BARRA LATERAL (SIDEBAR)
# ===============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942813.png", width=80)
    st.title("SISTEMA LOGÍSTICO")
    st.markdown("---")
    
    # Selector de Rol
    modo_seleccionado = st.radio(
        "Selecciona tu Perfil:", 
        ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0 # Por defecto Técnico para facilidad
    )
    
    st.markdown("---")
    st.caption("© 2026 - ITA Radian")
    st.caption("Versión 5.0 Ultimate")

# ===============================================================================
# SECCIÓN 8: VISTA DEL TÉCNICO (PORTAL DE DESCARGA SIMPLIFICADO)
# ===============================================================================

if modo_seleccionado == "👷 TÉCNICO":
    st.markdown('<div class="header-tecnico">🚛 ZONA DE DESCARGA DE RUTAS</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>Bienvenido. Selecciona tu nombre para descargar tu programación del día.</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 1. Escanear carpetas disponibles
    tecnicos_disponibles = []
    if os.path.exists(CARPETA_PUBLICA):
        items = os.listdir(CARPETA_PUBLICA)
        # Filtramos solo directorios
        tecnicos_disponibles = sorted([d for d in items if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    
    # 2. Lógica de visualización
    if not tecnicos_disponibles:
        st.warning("⏳ Aún no se han publicado las rutas del día.")
        st.info("Por favor espera a que el Coordinador publique la programación o recarga la página.")
        if st.button("🔄 Consultar Nuevamente", type="primary"):
            st.rerun()
    else:
        # Selector Gigante
        seleccion_nombre = st.selectbox(
            "👇 BUSCA TU NOMBRE AQUÍ:", 
            ["-- Seleccionar --"] + tecnicos_disponibles
        )
        
        if seleccion_nombre != "-- Seleccionar --":
            # Construir rutas de archivos
            ruta_carpeta_tec = os.path.join(CARPETA_PUBLICA, seleccion_nombre)
            archivo_hoja_ruta = os.path.join(ruta_carpeta_tec, "1_HOJA_DE_RUTA.pdf")
            archivo_legalizacion = os.path.join(ruta_carpeta_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"### Hola, **{seleccion_nombre}**. Aquí tienes tus documentos:")
            
            col_ruta, col_leg = st.columns(2)
            
            # --- TARJETA 1: HOJA DE RUTA ---
            with col_ruta:
                st.markdown("""
                <div class="status-card">
                    <h4>📄 1. Hoja de Ruta</h4>
                    <p>Contiene el listado de visitas, direcciones y medidores.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(archivo_hoja_ruta):
                    with open(archivo_hoja_ruta, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR RUTA",
                            data=f,
                            file_name=f"Ruta_{seleccion_nombre}.pdf",
                            mime="application/pdf",
                            key="btn_dl_ruta"
                        )
                else:
                    st.error("❌ Archivo no disponible")

            # --- TARJETA 2: PAQUETE DE LEGALIZACIÓN ---
            with col_leg:
                st.markdown("""
                <div class="status-card">
                    <h4>📂 2. Paquete de Pólizas</h4>
                    <p>Pólizas agrupadas para legalización (si aplica).</p>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(archivo_legalizacion):
                    with open(archivo_legalizacion, "rb") as f:
                        st.download_button(
                            label="⬇️ DESCARGAR PAQUETE",
                            data=f,
                            file_name=f"Legalizacion_{seleccion_nombre}.pdf",
                            mime="application/pdf",
                            key="btn_dl_leg"
                        )
                else:
                    st.info("ℹ️ Hoy no tienes pólizas asignadas.")

# ===============================================================================
# SECCIÓN 9: VISTA DEL ADMINISTRADOR (PANEL DE CONTROL TOTAL)
# ===============================================================================

elif modo_seleccionado == "⚙️ ADMINISTRADOR":
    st.header("⚙️ Panel de Gestión Logística - Modo Admin")
    
    # Login simple pero efectivo
    password_input = st.text_input("Ingrese Contraseña de Administrador:", type="password")
    
    if password_input == "ita2026": # CONTRASEÑA DE ACCESO
        
        # CREACIÓN DE LAS 4 PESTAÑAS FUNDAMENTALES
        tab_base, tab_carga, tab_manual, tab_publicar = st.tabs([
            "1. 🗃️ Base Operarios", 
            "2. ⚖️ Carga y Balanceo", 
            "3. 🛠️ Ajuste Manual", 
            "4. 🌍 Publicar y Descargar"
        ])
        
        # -----------------------------------------------------------------------
        # PESTAÑA 1: BASE DE OPERARIOS (MAESTRO)
        # -----------------------------------------------------------------------
        with tab_base:
            st.subheader("Configuración de la Cuadrilla")
            st.markdown("Carga aquí el archivo que relaciona **Barrios** con **Técnicos**.")
            
            maestro_upload = st.file_uploader("Subir Maestro de Operarios (Excel/CSV)", type=["xlsx", "csv"])
            
            if maestro_upload:
                with st.spinner("Procesando maestro..."):
                    st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_upload)
                st.success(f"✅ Base de datos actualizada: {len(st.session_state['mapa_actual'])} barrios cargados.")
            
            # Visor de estado actual
            if st.session_state['mapa_actual']:
                num_tecnicos = len(set(st.session_state['mapa_actual'].values()))
                st.info(f"Estado: {num_tecnicos} técnicos activos en la base de datos.")
            else:
                st.warning("⚠️ El sistema está vacío. Carga el maestro para comenzar.")

        # -----------------------------------------------------------------------
        # PESTAÑA 2: CARGA Y BALANCEO AUTOMÁTICO
        # -----------------------------------------------------------------------
        with tab_carga:
            st.subheader("Procesamiento Diario")
            
            col_up1, col_up2 = st.columns(2)
            
            # UPLOAD 1: PÓLIZAS
            with col_up1: 
                st.markdown("##### 1. PDF de Pólizas (Opcional)")
                pdf_polizas_up = st.file_uploader("Sube el PDF con todas las pólizas", type="pdf")
                
                # Botón de escaneo manual (por si acaso)
                if pdf_polizas_up:
                    if st.button("🔄 Escanear PDF Manualmente"):
                        with st.spinner("Analizando PDF..."):
                            st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(pdf_polizas_up)
                            st.success(f"✅ {len(st.session_state['mapa_polizas_cargado'])} Pólizas extraídas.")

            # UPLOAD 2: EXCEL DE RUTA
            with col_up2: 
                st.markdown("##### 2. Excel de Ruta (Obligatorio)")
                excel_ruta_up = st.file_uploader("Sube el archivo Excel del día", type=["xlsx", "csv"])
            
            # LÓGICA DE PROCESAMIENTO
            lista_tecnicos_activos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            if excel_ruta_up and lista_tecnicos_activos:
                try:
                    # Lectura del Excel
                    if excel_ruta_up.name.endswith('.csv'): 
                        df_ruta = pd.read_csv(excel_ruta_up, sep=None, engine='python', encoding='utf-8-sig')
                    else: 
                        df_ruta = pd.read_excel(excel_ruta_up)
                    
                    columnas_excel = list(df_ruta.columns)
                    
                    st.divider()
                    st.markdown("#### Configuración de Parámetros")
                    
                    # 1. Tabla de Cupos Editables
                    df_cupos = pd.DataFrame({"Técnico": lista_tecnicos_activos, "Cupo": [35]*len(lista_tecnicos_activos)})
                    editor_cupos = st.data_editor(
                        df_cupos, 
                        column_config={"Cupo": st.column_config.NumberColumn(min_value=1, max_value=200)}, 
                        hide_index=True,
                        use_container_width=True
                    )
                    LIMITES_CUPOS = dict(zip(editor_cupos["Técnico"], editor_cupos["Cupo"]))
                    
                    # 2. Mapeo de Columnas Inteligente
                    def buscar_indice(keywords): 
                        for i, c in enumerate(columnas_excel): 
                            for k in keywords: 
                                if k in str(c).upper(): return i
                        return 0
                    
                    mc1, mc2, mc3 = st.columns(3)
                    sel_barrio = mc1.selectbox("Columna BARRIO", columnas_excel, index=buscar_indice(['BARRIO', 'SECTOR']))
                    sel_direcc = mc2.selectbox("Columna DIRECCION", columnas_excel, index=buscar_indice(['DIR', 'DIRECCION']))
                    sel_cuenta = mc3.selectbox("Columna CUENTA", columnas_excel, index=buscar_indice(['CUENTA', 'POLIZA']))
                    sel_medidor = st.selectbox("Columna MEDIDOR", ["NO TIENE"]+columnas_excel, index=buscar_indice(['MEDIDOR'])+1)
                    sel_cliente = st.selectbox("Columna CLIENTE", ["NO TIENE"]+columnas_excel, index=buscar_indice(['CLIENTE', 'NOMBRE'])+1)
                    
                    mapa_columnas = {
                        'BARRIO': sel_barrio, 
                        'DIRECCION': sel_direcc, 
                        'CUENTA': sel_cuenta, 
                        'MEDIDOR': sel_medidor if sel_medidor!="NO TIENE" else None, 
                        'CLIENTE': sel_cliente if sel_cliente!="NO TIENE" else None
                    }
                    
                    st.divider()
                    
                    # BOTÓN GRANDE DE EJECUCIÓN
                    if st.button("🚀 EJECUTAR BALANCEO AUTOMÁTICO", type="primary"):
                        
                        # PASO A: AUTO-ESCANEO DE PÓLIZAS (SEGURIDAD V4.1)
                        # Si el usuario subió PDF pero olvidó darle al botón de escanear, lo hacemos nosotros.
                        if pdf_polizas_up and not st.session_state['mapa_polizas_cargado']:
                            with st.spinner("⚠️ Detecté que no escaneaste el PDF. Escaneando automáticamente..."):
                                st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(pdf_polizas_up)
                                st.toast(f"✅ Auto-escaneo completado: {len(st.session_state['mapa_polizas_cargado'])} pólizas.", icon="📂")

                        with st.spinner("Asignando zonas, ordenando direcciones y balanceando cargas..."):
                            df = df_ruta.copy()
                            
                            # A. Asignación Inicial
                            df['TECNICO_IDEAL'] = df[sel_barrio].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                            df['TECNICO_FINAL'] = df['TECNICO_IDEAL']
                            df['ORIGEN_REAL'] = None # Para marcar apoyos
                            
                            # B. Ordenamiento Natural (Tuplas) - CRÍTICO PARA RUTA LÓGICA
                            df['SORT_KEY'] = df[sel_direcc].astype(str).apply(natural_sort_key)
                            df = df.sort_values(by=[sel_barrio, 'SORT_KEY'])
                            
                            # C. Algoritmo de Balanceo
                            conteo_actual = df['TECNICO_IDEAL'].value_counts()
                            
                            for tech in [t for t in lista_tecnicos_activos if conteo_actual.get(t, 0) > LIMITES_CUPOS.get(t, 35)]:
                                limite = LIMITES_CUPOS.get(tech, 35)
                                filas_tech = df[df['TECNICO_FINAL'] == tech]
                                excedente = len(filas_tech) - limite
                                
                                if excedente > 0:
                                    # Tomamos los últimos registros (generalmente los más lejanos del barrio)
                                    indices_mover = filas_tech.index[-excedente:]
                                    
                                    # Buscar quien tiene menos carga
                                    conteo_live = df['TECNICO_FINAL'].value_counts()
                                    candidato = sorted([t for t in lista_tecnicos_activos if t != tech], key=lambda x: conteo_live.get(x, 0))[0]
                                    
                                    # Reasignar
                                    df.loc[indices_mover, 'TECNICO_FINAL'] = candidato
                                    df.loc[indices_mover, 'ORIGEN_REAL'] = tech # Marca de donde vino
                            
                            # Guardar resultado en sesión
                            st.session_state['df_simulado'] = df.drop(columns=['SORT_KEY'])
                            st.session_state['col_map_final'] = mapa_columnas
                            st.success("✅ Balanceo completado exitosamente.")
                            st.info("Ahora puedes ir a la Pestaña 3 para ajustes manuales o Pestaña 4 para publicar.")
                            
                except Exception as e:
                    st.error(f"Error procesando archivo: {e}")

        # -----------------------------------------------------------------------
        # PESTAÑA 3: AJUSTE MANUAL (MÓDULO RECUPERADO)
        # -----------------------------------------------------------------------
        with tab_manual:
            st.header("🛠️ Ajuste Manual de Asignaciones")
            st.markdown("Mueve barrios completos de un técnico a otro si el balanceo automático no fue preciso.")
            
            if st.session_state['df_simulado'] is not None:
                df_work = st.session_state['df_simulado']
                cols_map = st.session_state['col_map_final']
                col_barrio_work = cols_map['BARRIO']
                tecnicos_en_ruta = sorted(df_work['TECNICO_FINAL'].unique())

                # --- PANEL DE CONTROL DE MOVIMIENTOS ---
                c_origen, c_barrio, c_destino, c_accion = st.columns([1.5, 1.5, 1.5, 1])
                
                with c_origen:
                    origen_sel = st.selectbox("1. Técnico Origen:", ["-"] + list(tecnicos_en_ruta))
                
                with c_barrio:
                    if origen_sel != "-":
                        # Filtrar barrios que tiene ese técnico
                        barrios_tech = df_work[df_work['TECNICO_FINAL'] == origen_sel][col_barrio_work].value_counts()
                        # Formato: "BARRIO (Cantidad)"
                        opciones_barrio = [f"{k} ({v})" for k, v in barrios_tech.items()]
                        barrio_sel = st.selectbox("2. Barrio a Mover:", opciones_barrio)
                    else:
                        barrio_sel = None
                        st.selectbox("2. Barrio a Mover:", ["-"], disabled=True)

                with c_destino:
                    destino_sel = st.selectbox("3. Técnico Destino:", ["-"] + lista_tecnicos_activos)

                with c_accion:
                    st.write("") # Espaciador vertical
                    st.write("") 
                    if st.button("🔄 MOVER BARRIO", type="primary"):
                        if barrio_sel and destino_sel != "-" and origen_sel != "-":
                            # Extraer nombre limpio del barrio (quitar el conteo)
                            nombre_barrio_real = barrio_sel.rsplit(" (", 1)[0]
                            
                            # Aplicar filtro y cambio en el Dataframe
                            mascara = (df_work['TECNICO_FINAL'] == origen_sel) & (df_work[col_barrio_work] == nombre_barrio_real)
                            
                            df_work.loc[mascara, 'TECNICO_FINAL'] = destino_sel
                            df_work.loc[mascara, 'ORIGEN_REAL'] = origen_sel # Marcar como Apoyo
                            
                            # Guardar y Recargar
                            st.session_state['df_simulado'] = df_work
                            st.rerun() # Recarga la página para ver cambios instantáneamente

                st.divider()
                st.subheader("📊 Vista Previa de Cargas (Tiempo Real)")
                
                # Visualización de tarjetas de carga
                cols_grid = st.columns(2)
                for idx, tec in enumerate(tecnicos_en_ruta):
                    with cols_grid[idx % 2]:
                        sub_df = df_work[df_work['TECNICO_FINAL'] == tec]
                        
                        # Agrupar por barrio para resumen
                        resumen_barrios = sub_df.groupby([col_barrio_work, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='Visitas')
                        
                        # Marcar apoyos visualmente en la tabla
                        resumen_barrios['Barrio'] = resumen_barrios.apply(
                            lambda x: f"⚠️ {x[col_barrio_work]} (APOYO)" if pd.notna(x['ORIGEN_REAL']) else x[col_barrio_work], 
                            axis=1
                        )
                        
                        with st.expander(f"👷 **{tec}** | Total: {len(sub_df)} visitas", expanded=True):
                            st.dataframe(resumen_barrios[['Barrio', 'Visitas']], hide_index=True, use_container_width=True)

            else:
                st.info("⚠️ Primero debes cargar y procesar la ruta en la Pestaña 2.")

        # -----------------------------------------------------------------------
        # PESTAÑA 4: PUBLICACIÓN Y DESCARGAS
        # -----------------------------------------------------------------------
        with tab_publicar:
            st.header("🌍 Gestión Final y Distribución")
            
            if st.session_state['df_simulado'] is not None:
                df_final = st.session_state['df_simulado']
                mapa_cols_final = st.session_state['col_map_final']
                polizas_cargadas = st.session_state['mapa_polizas_cargado']
                
                tecnicos_finales = [t for t in df_final['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                # --- AVISO SOBRE PÓLIZAS ---
                if not polizas_cargadas:
                    st.warning("⚠️ ADVERTENCIA: No se cargaron pólizas. Las carpetas de legalización estarán vacías.")
                else:
                    st.success(f"✅ {len(polizas_cargadas)} Pólizas listas para distribuir.")

                # --- SECCIÓN A: PUBLICACIÓN WEB ---
                st.markdown("### 1. Publicar en Portal Web (Técnicos)")
                st.info("Al hacer clic, se limpiarán los archivos de ayer y se generarán los nuevos PDFs para descarga.")
                
                if st.button("📢 PUBLICAR RUTAS AHORA", type="primary"):
                    limpiar_carpeta_publica()
                    barra_progreso = st.progress(0)
                    
                    for i, tec in enumerate(tecnicos_finales):
                        # Preparar Datos
                        df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                        
                        # RE-ORDENAMIENTO FINAL (Para asegurar coherencia)
                        df_t['SORT_TEMP'] = df_t[mapa_cols_final['DIRECCION']].astype(str).apply(natural_sort_key)
                        df_t = df_t.sort_values(by=[mapa_cols_final['BARRIO'], 'SORT_TEMP']).drop(columns=['SORT_TEMP'])
                        
                        # Crear carpeta segura
                        nombre_seguro = str(tec).replace(" ", "_")
                        ruta_carpeta_tec = os.path.join(CARPETA_PUBLICA, nombre_seguro)
                        os.makedirs(ruta_carpeta_tec, exist_ok=True)
                        
                        # A. GENERAR HOJA DE RUTA
                        bytes_hoja = crear_pdf_lista_final(df_t, tec, mapa_cols_final)
                        with open(os.path.join(ruta_carpeta_tec, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(bytes_hoja)
                        
                        # B. GENERAR PAQUETE LEGALIZACIÓN (MERGE)
                        if polizas_cargadas:
                            merger = fitz.open()
                            count_pols = 0
                            for _, row in df_t.iterrows():
                                cta = normalizar_numero(str(row[mapa_cols_final['CUENTA']]))
                                if cta in polizas_cargadas:
                                    with fitz.open(stream=polizas_cargadas[cta], filetype="pdf") as tmp:
                                        merger.insert_pdf(tmp)
                                    count_pols += 1
                            
                            if count_pols > 0:
                                with open(os.path.join(ruta_carpeta_tec, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f:
                                    f.write(merger.tobytes())
                            merger.close()
                        
                        barra_progreso.progress((i + 1) / len(tecnicos_finales))
                        
                    st.success(f"✅ ¡Publicación Exitosa! {len(tecnicos_finales)} técnicos ya pueden descargar.")
                    st.balloons()

                st.divider()
                
                # --- SECCIÓN B: DESCARGA ADMIN (ZIP COMPLETO) ---
                st.markdown("### 2. Descarga Administrativa (Respaldo Total)")
                st.caption("Genera un ZIP con la estructura completa de carpetas (1, 2, 3, 4) + Banco de Pólizas.")
                
                if st.button("📦 GENERAR ZIP MAESTRO"):
                    with st.spinner("Compilando estructura completa..."):
                        zip_memoria = io.BytesIO()
                        
                        with zipfile.ZipFile(zip_memoria, "w") as zf:
                            
                            # CARPETA 00: BANCO DE PÓLIZAS (CRÍTICO - LO QUE FALTABA ANTES)
                            if polizas_cargadas:
                                for k, v in polizas_cargadas.items():
                                    zf.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                            
                            # CARPETA 00: CONSOLIDADO EXCEL
                            excel_total = io.BytesIO()
                            with pd.ExcelWriter(excel_total, engine='xlsxwriter') as w: df_final.to_excel(w, index=False)
                            zf.writestr("00_CONSOLIDADO_GENERAL.xlsx", excel_total.getvalue())

                            # CARPETAS POR TÉCNICO
                            for tec in tecnicos_finales:
                                safe_name = str(tec).replace(" ", "_")
                                df_t = df_final[df_final['TECNICO_FINAL'] == tec].copy()
                                
                                # Ordenar
                                df_t['SORT_TEMP'] = df_t[mapa_cols_final['DIRECCION']].astype(str).apply(natural_sort_key)
                                df_t = df_t.sort_values(by=[mapa_cols_final['BARRIO'], 'SORT_TEMP']).drop(columns=['SORT_TEMP'])
                                
                                # 1. HOJA DE RUTA
                                pdf_ruta = crear_pdf_lista_final(df_t, tec, mapa_cols_final)
                                zf.writestr(f"{safe_name}/1_HOJA_DE_RUTA.pdf", pdf_ruta)
                                
                                # 2. TABLA DIGITAL
                                excel_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                    df_t.to_excel(writer, index=False)
                                zf.writestr(f"{safe_name}/2_TABLA_DIGITAL.xlsx", excel_buffer.getvalue())
                                
                                # 3 y 4. PÓLIZAS (MERGE E INDIVIDUAL)
                                if polizas_cargadas:
                                    merger = fitz.open()
                                    count_p = 0
                                    for _, row in df_t.iterrows():
                                        cta = normalizar_numero(str(row[mapa_cols_final['CUENTA']]))
                                        if cta in polizas_cargadas:
                                            # CARPETA 4: INDIVIDUALES
                                            zf.writestr(f"{safe_name}/4_POLIZAS_INDIVIDUALES/{cta}.pdf", polizas_cargadas[cta])
                                            # CARPETA 3: MERGE
                                            with fitz.open(stream=polizas_cargadas[cta], filetype="pdf") as tmp:
                                                merger.insert_pdf(tmp)
                                            count_p += 1
                                    
                                    if count_p > 0:
                                        zf.writestr(f"{safe_name}/3_PAQUETE_LEGALIZACION.pdf", merger.tobytes())
                                    merger.close()

                        st.session_state['zip_admin_ready'] = zip_memoria.getvalue()
                        st.success("ZIP Generado correctamente.")

                # BOTÓN DE DESCARGA ZIP
                if st.session_state['zip_admin_ready']:
                    st.download_button(
                        label="⬇️ DESCARGAR ZIP ADMINISTRATIVO",
                        data=st.session_state['zip_admin_ready'],
                        file_name="Logistica_Completa_ITA.zip",
                        mime="application/zip"
                    )
            else:
                st.info("Procesa la ruta primero en la pestaña 2.")

    elif password_input:
        st.error("❌ Contraseña Incorrecta")

# ===============================================================================
# FIN DEL SISTEMA
# ===============================================================================
