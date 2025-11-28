import pandas as pd
from pymongo import MongoClient
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import base64
import os

# ======================================================
# 1. Conexión a MongoDB (compatible con Render)
# ======================================================
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://erick:kikotrukini1@cluster0.aaonird.mongodb.net/"
)

client = MongoClient(MONGO_URI)
db = client["cfe_db"]

collection_nodos = db["nodos"]
df = pd.DataFrame(list(collection_nodos.find()))

if "_id" in df.columns:
    df["_id"] = df["_id"].astype(str)


# ======================================================
# 2. Filtrar estados permitidos
# ======================================================
estados_permitidos = [
    "CIUDAD DE MEXICO",
    "GUERRERO",
    "HIDALGO",
    "MEXICO",
    "MICHOACAN DE OCAMPO",
    "MORELOS",
    "PUEBLA"
]

df = df[df["ESTADO"].isin(estados_permitidos)]


# ======================================================
# 3. Función para cargar imágenes desde /assets
# ======================================================
def load_asset_image(filename):
    path = f"assets/{filename}"
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{encoded}"


stellar_logo = load_asset_image("stellar.png")
cfe_logo = load_asset_image("cfe.png")


# ======================================================
# 4. Valores DEFAULT
# ======================================================
DEFAULT_ESTADO = "CIUDAD DE MEXICO"
DEFAULT_MUNICIPIO = "AZCAPOTZALCO"
DEFAULT_NODO = "01PXA-85"

CFE_VERDE_OSCURO = "#003B2D"
CFE_GRIS = "#E5E5E5"

# Paleta pastel
PASTEL_PML = "#4c72b0"
PASTEL_PROPHET = "#55a868"
PASTEL_XGB = "#c44e52"


# ======================================================
# 5. App Dash
# ======================================================
app = Dash(__name__)
server = app.server  # Render usa "server" para ejecutar


# ======================================================
# 6. LAYOUT COMPLETO
# ======================================================
app.layout = html.Div(
    style={"backgroundColor": CFE_VERDE_OSCURO, "padding": "20px", "color": "white"},
    children=[

        # ------------------- HEADER -------------------
        html.Div([
            html.Img(src=stellar_logo, style={"height": "70px"}),

            html.H1(
                "Tablero de Control Nodos CFE",
                style={"flex": "1", "textAlign": "center", "color": CFE_GRIS, "fontSize": "38px", "margin": "0"}
            ),

            html.Img(src=cfe_logo, style={"height": "70px"})
        ], style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": "20px"
        }),

        # ---------------- CONTROLES ----------------
        html.Div([
            html.Div([
                html.Label("Estado"),
                dcc.Dropdown(
                    id="dropdown-estado",
                    options=[{"label": x, "value": x} for x in sorted(df["ESTADO"].unique())],
                    value=DEFAULT_ESTADO,
                    style={"color": "black"},
                )
            ], style={"flex": 1}),

            html.Div([
                html.Label("Municipio"),
                dcc.Dropdown(
                    id="dropdown-municipio",
                    value=DEFAULT_MUNICIPIO,
                    style={"color": "black"},
                )
            ], style={"flex": 1}),

            html.Div([
                html.Label("Nodo"),
                dcc.Dropdown(
                    id="dropdown-nodo",
                    value=DEFAULT_NODO,
                    style={"color": "black"},
                )
            ], style={"flex": 1})
        ],
        style={"display": "flex", "gap": "10px", "marginBottom": "20px"}),

        # ---------------- MAPA ----------------
        dcc.Graph(id="mapa-mexico"),

        # ---------------- INDICADORES ----------------
        html.Div(
            id="indicadores-costos",
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "marginTop": "30px",
                "marginBottom": "30px",
                "gap": "20px"
            }
        ),

        # ---------------- SERIES ----------------
        html.Div([
            dcc.Graph(id="serie-modelos", style={"height": "500px"}),
            dcc.Graph(id="serie-anomalias", style={"height": "500px"}),
            dcc.Graph(id="grafica-estrategia", style={"height": "500px"}),
        ])
    ]
)


# ======================================================
# 7. CALLBACKS DE DROPDOWNS
# ======================================================
@app.callback(
    Output("dropdown-municipio", "options"),
    Input("dropdown-estado", "value")
)
def actualizar_municipios(estado):
    municipios = df[df["ESTADO"] == estado]["MUNICIPIO"].unique()
    return [{"label": m, "value": m} for m in sorted(municipios)]


@app.callback(
    Output("dropdown-nodo", "options"),
    [Input("dropdown-estado", "value"), Input("dropdown-municipio", "value")]
)
def actualizar_nodos(estado, municipio):
    nodos = df[(df["ESTADO"] == estado) & (df["MUNICIPIO"] == municipio)]["NODO"].unique()
    return [{"label": n, "value": n} for n in sorted(nodos)]


# ======================================================
# 8. MAPA (ya corregido y centrado)
# ======================================================
@app.callback(
    Output("mapa-mexico", "figure"),
    [Input("dropdown-estado", "value"),
     Input("dropdown-municipio", "value"),
     Input("dropdown-nodo", "value")]
)
def actualizar_mapa(estado, municipio, nodo):

    df_plot = df.copy()
    df_plot["color"] = "#2ca02c"

    df_plot.loc[
        (df_plot["ESTADO"] == estado) &
        (df_plot["MUNICIPIO"] == municipio) &
        (df_plot["NODO"] == nodo),
        "color"
    ] = "red"

    fig = px.scatter_map(
        df_plot,
        lat="lat",
        lon="long",
        color="color",
        hover_name="MUNICIPIO",
        hover_data=["ESTADO", "NODO"],
        zoom=5.8,
        center={"lat": 20.5, "lon": -102},   # centrar México
        height=500,
    )

    fig.update_layout(
        map_style="open-street-map",
        paper_bgcolor=CFE_VERDE_OSCURO,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig


# ======================================================
# 9. SERIES + INDICADORES (NO CAMBIADO)
# ======================================================
@app.callback(
    [Output("indicadores-costos", "children"),
     Output("serie-modelos", "figure"),
     Output("serie-anomalias", "figure"),
     Output("grafica-estrategia", "figure")],
    Input("dropdown-nodo", "value")
)
def actualizar_series(nodo):

    fig_empty = go.Figure()
    fig_empty.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font_color="black",
        title="Selecciona un nodo"
    )

    if not nodo:
        return [], fig_empty, fig_empty, fig_empty

    # ===================== INDICADORES =====================
    row = db["costos_acumulados"].find_one({"nodo": nodo})

    if not row:
        indicadores_html = html.Div("Sin datos de costos", style={"color": "white"})
    else:
        indicadores_html = [
            html.Div([
                html.H4("MDA acumulado"),
                html.H3(f"${row['MDA_acum']:,.2f}")
            ], style={"background": "white", "color": "black", "padding": "15px",
                      "borderRadius": "10px", "flex": "1", "textAlign": "center"}),

            html.Div([
                html.H4("MTR acumulado"),
                html.H3(f"${row['MTR_acum']:,.2f}")
            ], style={"background": "white", "color": "black", "padding": "15px",
                      "borderRadius": "10px", "flex": "1", "textAlign": "center"}),

            html.Div([
                html.H4("Estrategia acumulada"),
                html.H3(f"${row['Nuestra_estrategia_acum']:,.2f}")
            ], style={"background": "white", "color": "black", "padding": "15px",
                      "borderRadius": "10px", "flex": "1", "textAlign": "center"}),

            html.Div([
                html.H4("Ahorro vs MDA"),
                html.H3(f"${row['ahorro_vs_MDA']:,.2f}")
            ], style={"background": "white", "color": "black", "padding": "15px",
                      "borderRadius": "10px", "flex": "1", "textAlign": "center"}),

            html.Div([
                html.H4("Ahorro vs MTR"),
                html.H3(f"${row['ahorro_vs_MTR']:,.2f}")
            ], style={"background": "white", "color": "black", "padding": "15px",
                      "borderRadius": "10px", "flex": "1", "textAlign": "center"}),
        ]

    # ============= LECTURA DE DATOS DEL NODO =============
    coll_name = "nodo_" + nodo.replace("-", "_")
    df_nodo = pd.DataFrame(list(db[coll_name].find()))

    if df_nodo.empty:
        return indicadores_html, fig_empty, fig_empty, fig_empty

    # Convertir fecha-hora
    df_nodo["fecha"] = df_nodo["fecha"].astype(str)
    df_nodo["hora"] = df_nodo["hora"].astype(int)
    df_nodo["fecha_hora"] = pd.to_datetime(df_nodo["fecha"]) + pd.to_timedelta(df_nodo["hora"] - 1, unit="h")

    for col in ["pml", "y_prophet", "y_xgboost"]:
        df_nodo[col] = pd.to_numeric(df_nodo[col], errors="coerce")

    df_nodo = df_nodo.sort_values("fecha_hora")

    ultimo_mes = df_nodo["fecha_hora"].max() - pd.Timedelta(days=30)
    df_mes = df_nodo[df_nodo["fecha_hora"] >= ultimo_mes]

    # ==================== FIGURA 1 ====================
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_mes["fecha_hora"], y=df_mes["pml"],
                              mode="lines", name="PML",
                              line=dict(color=PASTEL_PML, width=2)))
    fig1.add_trace(go.Scatter(x=df_mes["fecha_hora"], y=df_mes["y_prophet"],
                              mode="lines", name="Prophet",
                              line=dict(color=PASTEL_PROPHET, width=2)))
    fig1.add_trace(go.Scatter(x=df_mes["fecha_hora"], y=df_mes["y_xgboost"],
                              mode="lines", name="XGBoost",
                              line=dict(color=PASTEL_XGB, width=2)))
    fig1.update_layout(
        title=f"Último Mes - PML vs Modelos ({nodo})",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font_color="black",
        height=500
    )

    # ==================== FIGURA 2 ====================
    df_anom = df_nodo[df_nodo["anomalia_consenso"] == -1]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_nodo["fecha_hora"], y=df_nodo["pml"],
                              mode="lines", name="PML",
                              line=dict(color=PASTEL_PML, width=2)))
    fig2.add_trace(go.Scatter(x=df_anom["fecha_hora"], y=df_anom["pml"],
                              mode="markers", name="Anomalía",
                              marker=dict(color="red", size=8)))
    fig2.update_layout(
        title=f"Anomalías Consenso ({nodo})",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font_color="black",
        height=500
    )

    # ==================== FIGURA 3 ====================
    coll_estrategia = nodo.replace("-", "_") + "_estrategia"
    df_est = pd.DataFrame(list(db[coll_estrategia].find()))

    if df_est.empty or "timestamp" not in df_est.columns:
        fig3 = fig_empty
    else:
        df_est["timestamp"] = pd.to_datetime(df_est["timestamp"])
        df_est = df_est.sort_values("timestamp")

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df_est["timestamp"], y=df_est["Nuestra_estrategia_acum"],
                                  mode="lines", name="Estrategia Inteligente",
                                  line=dict(color="purple", width=3)))
        fig3.add_trace(go.Scatter(x=df_est["timestamp"], y=df_est["MDA_acum"],
                                  mode="lines", name="Siempre MDA",
                                  line=dict(color="blue", width=3, dash="dash")))
        fig3.add_trace(go.Scatter(x=df_est["timestamp"], y=df_est["MTR_acum"],
                                  mode="lines", name="Siempre MTR",
                                  line=dict(color="green", width=3, dash="dot")))

        fig3.update_layout(
            title=f"Estrategia Inteligente vs MDA vs MTR ({nodo})",
            paper_bgcolor="white",
            plot_bgcolor="white",
            font_color="black",
            height=500
        )

    return indicadores_html, fig1, fig2, fig3


# ======================================================
# 10. EJECUCIÓN (Render)
# ======================================================
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=False)


