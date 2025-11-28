import os
import pandas as pd
from pymongo import MongoClient

# =================================================
# 1. CONFIGURACIÓN
# =================================================
CARPETA = r"C:\Users\GoodM\Downloads\datos_para_plots\datos_para_plots"
CARPETA_ANOM = r"C:\Users\GoodM\Downloads\con_anomalias_centro\con_anomalias_centro"

client = MongoClient("mongodb+srv://erick:kikotrukini1@cluster0.aaonird.mongodb.net/")
db = client["cfe_db"]   # base de datos general


# =================================================
# 2. PROCESAR ARCHIVOS CSV
# =================================================
archivos = [f for f in os.listdir(CARPETA) if f.endswith(".csv")]

for archivo in archivos:
    ruta = os.path.join(CARPETA, archivo)

    # Extraer nombre del nodo desde el archivo
    nodo = archivo.split("_")[0]   # Ejemplo: 01TCM-230

    # Convertir a nombre válido de colección
    nombre_coleccion = "nodo_" + nodo.replace("-", "_")

    print(f"\n📌 Procesando archivo: {archivo}")
    print(f"   → Colección: {nombre_coleccion}")

    try:
        df = pd.read_csv(ruta)

        # Agregar columna del nodo (útil para dashboards)
        df["NODO"] = nodo

        # Convertir fechas si existen
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"])

            # FILTRAR SOLO LOS ÚLTIMOS 2 MESES
            fecha_max = df["fecha"].max()
            fecha_limite = fecha_max - pd.DateOffset(months=2)
            df = df[df["fecha"] >= fecha_limite]

            print(f"   → Filtrado a últimos 2 meses: {len(df)} filas")

        # =========================================================
        # 🧹 NUEVO: ELIMINAR anomalia_consenso QUE VIENE EN EL CSV
        # =========================================================
        if "anomalia_consenso" in df.columns:
            df.drop(columns=["anomalia_consenso"], inplace=True)

        # =========================================================
        # 🔥 MERGE CON CSV DE ANOMALÍAS POR NODO
        # =========================================================

        # Buscar un archivo de anomalías que contenga el nodo
        archivo_anom = None
        for a in os.listdir(CARPETA_ANOM):
            if nodo in a:   # PML_01TPA-115.csv
                archivo_anom = a
                break

        if archivo_anom:
            ruta_anom = os.path.join(CARPETA_ANOM, archivo_anom)
            df_anom = pd.read_csv(ruta_anom)

            # Convertir fecha a datetime
            df_anom["fecha"] = pd.to_datetime(df_anom["fecha"])

            # MERGE por nodo-fecha-hora
            df = df.merge(
                df_anom[["nodo", "fecha", "hora", "anomalia_consenso"]],
                how="left",
                left_on=["NODO", "fecha", "hora"],
                right_on=["nodo", "fecha", "hora"]
            )

            # Quitar la columna duplicada "nodo"
            if "nodo" in df.columns:
                df.drop(columns=["nodo"], inplace=True)

            print(f"   → Anomalías añadidas desde: {archivo_anom}")

        else:
            df["anomalia_consenso"] = None
            print("   ⚠ No se encontró archivo de anomalías para este nodo")

        # =============================
        # QUEDARSE SOLO CON COLUMNAS NECESARIAS
        # =============================
        columnas_necesarias = ["NODO", "fecha", "hora", "pml", "y_prophet", "y_xgboost", "anomalia_consenso"]
        df = df[[c for c in columnas_necesarias if c in df.columns]]

        # Crear colección
        coleccion = db[nombre_coleccion]

        # Insertar datos filtrados
        if len(df) > 0:
            coleccion.insert_many(df.to_dict("records"))

        print(f"   ✔ {len(df)} documentos insertados")

    except Exception as e:
        print(f"   ⚠ Error cargando {archivo}: {e}")

print("\n✔ Carga completada.")



