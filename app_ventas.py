import streamlit as st
import mysql.connector
import pandas as pd
import re
import os
from dotenv import load_dotenv
load_dotenv()  # Esto busca el archivo .env y carga las variables

# Prueba de diagnóstico rápida:
db_pass = os.getenv('DB_PASS')
print(f"La contraseña cargada es: {db_pass}")


# Cargar las variables del archivo .env
load_dotenv()

# PRUEBA DE DIAGNÓSTICO (Solo para ver en la terminal)
if not os.getenv("DB_PASS"):
    st.error("❌ El archivo .env no se cargó o está vacío.")
else:
    st.success("✅ Variables de entorno detectadas.")

def conectar_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Plásticos Esba - Sistema de Gestión", layout="wide")

    
    

def leer_xml_factura(xml_data):
    try:
        if isinstance(xml_data, (bytes, bytearray)):
            xml_str = xml_data.decode('utf-8', errors='ignore')
        else:
            xml_str = str(xml_data)

        # Limpieza de basura técnica
        xml_str = xml_str.replace('\\xef\\xbb\\xbf', '').replace('\\n', ' ').replace('\\r', '')
        if xml_str.startswith("b'") or xml_str.startswith('b"'):
            xml_str = xml_str[2:-1]

        # Extraer PRODUCTOS (Conceptos) con RegEx
        conceptos_raw = re.findall(r'<[^>]*Concepto([^>]+)>', xml_str, re.IGNORECASE)
        
        lista_productos = []
        for c in conceptos_raw:
            cant = re.search(r'cantidad="([^"]+)"', c, re.IGNORECASE)
            desc = re.search(r'descripcion="([^"]+)"', c, re.IGNORECASE)
            unit = re.search(r'valorUnitario="([^"]+)"', c, re.IGNORECASE)
            imp  = re.search(r'importe="([^"]+)"', c, re.IGNORECASE)
            
            lista_productos.append({
                "Cantidad": float(cant.group(1)) if cant else 0,
                "Descripción": desc.group(1) if desc else "S/D",
                "Precio Unit.": float(unit.group(1)) if unit else 0,
                "Importe": float(imp.group(1)) if imp else 0
            })
        return {"Productos": lista_productos}
    except Exception:
        return {"Productos": []}

# --- 2. ESTRUCTURA DE NAVEGACIÓN ---
st.title(" Panel de Control - Pandabolsas")

tab1, tab2, tab3 = st.tabs(["📈 Ventas", "📦 Inventario", "🧾 Visor CFDI"])

with tab1:
    st.subheader("Análisis de Ventas Históricas")
    st.info("Aquí irán tus gráficas de crecimiento.")

with tab2:
    st.subheader("Control de Inventario")
    st.info("Listado de existencias actuales.")

# --- 3. PESTAÑA DEL VISOR (t_venta_cfd) ---
with tab3:
    st.header("🔍 Auditor de Facturas (Tabla t_venta_cfd)")
    st.write("Consulta facturas 3.2 y 4.0 directamente de la tabla maestra.")
    
    id_busqueda = st.number_input("Introduce el ID de Venta:", value=330982, step=1)
    
    if st.button("Analizar Factura XML"):
        try:
            # Todo este bloque debe tener la misma sangría
            conn = conectar_db()
            query = f"""
                SELECT nombre, total, version, uuid, xml_timbrado 
                FROM t_venta_cfd 
                WHERE id_venta = {id_busqueda} 
                LIMIT 1
            """
            df_sql = pd.read_sql(query, conn)
            conn.close()

            if not df_sql.empty:
                fila = df_sql.iloc[0]
                datos_xml = leer_xml_factura(fila['xml_timbrado'])
                
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Cliente (DB)", fila['nombre'])
                with c2:
                    st.metric("Total (DB)", f"$ {float(fila['total']):,.2f}")
                with c3:
                    st.metric("Versión SAT", fila['version'])
                
                st.caption(f"**UUID:** {fila['uuid']}")
                
                st.subheader("📦 Detalle de Conceptos (Desde XML)")
                if datos_xml['Productos']:
                    df_prod = pd.DataFrame(datos_xml['Productos'])
                    st.dataframe(df_prod, use_container_width=True, hide_index=True)
                else:
                    st.warning("No se pudieron extraer productos del XML.")
                
                with st.expander("📄 Ver XML Crudo"):
                    st.text(fila['xml_timbrado'])
            else:
                st.error(f"No se encontró el ID {id_busqueda} en la base de datos.")

        except Exception as e:
            # Este 'except' debe estar alineado perfectamente con su 'try'
            st.error(f"Error técnico: {e}")