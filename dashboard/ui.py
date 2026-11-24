"""Aparência comum das telas, inspirada no Fluent 2 (Microsoft): cartões brancos
com sombra leve sobre fundo cinza, azul de marca #0F6CBD e fonte Segoe UI."""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

AZUL, AZUL_MEDIO, AZUL_CLARO, LARANJA, CINZA = "#0F6CBD", "#62ABF5", "#B4D6FA", "#E37D00", "#616161"
FONTE = "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, Helvetica Neue, sans-serif"

pio.templates["fluent"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONTE, size=12, color="#424242"),
        title=dict(font=dict(size=14, color="#242424", weight=600), x=0, xanchor="left", y=0.97),
        colorway=[AZUL, AZUL_MEDIO, LARANJA, AZUL_CLARO, CINZA],
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        margin=dict(l=8, r=8, t=52, b=8),
        xaxis=dict(showgrid=False, linecolor="#D1D1D1", ticks="", tickfont=dict(color="#616161")),
        yaxis=dict(gridcolor="#F0F0F0", zeroline=False, tickfont=dict(color="#616161")),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
        hoverlabel=dict(font=dict(family=FONTE), bgcolor="#FFFFFF", bordercolor="#E0E0E0"),
    )
)
pio.templates.default = "fluent"


def cabecalho(titulo, descricao=None):
    st.markdown(f"# {titulo}")
    if descricao:
        st.caption(descricao)


def inteiro(v):
    return f"{v:,.0f}".replace(",", ".")


def estilo():
    """Sombras e acabamento que o tema do Streamlit não cobre."""
    st.markdown(
        """<style>
        [data-testid="stMainBlockContainer"]{padding-top:2rem; max-width:1320px}
        /* cartões: fundo branco, borda sutil e sombra Fluent (shadow4) */
        [class*="st-key-card_"], [data-testid="stMetric"]{
            background:#FFFFFF; border-color:#E8E8E8 !important; border-radius:8px !important;
            box-shadow:0 0 2px rgba(0,0,0,.12), 0 2px 4px rgba(0,0,0,.14)}
        [data-testid="stMetricLabel"] p{font-size:.8rem; color:#616161; font-weight:400}
        /* navegação lateral: item ativo com barra azul à esquerda, como no NavDrawer */
        [data-testid="stSidebarNav"] a{border-radius:4px}
        [data-testid="stSidebarNav"] a[aria-current="page"]{background:#EBF3FC; box-shadow:inset 3px 0 0 #0F6CBD}
        [data-testid="stSidebarNav"] a[aria-current="page"] span{color:#0F6CBD; font-weight:600}
        [data-testid="stSidebarNavSeparator"]{display:none}
        </style>""",
        unsafe_allow_html=True,
    )


def estilo_totem():
    """Tela de toque: sem menu lateral, letra maior e alvos de pelo menos 64 px."""
    st.markdown(
        """<style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]{display:none}
        html{font-size:20px}
        [data-testid="stMainBlockContainer"]{max-width:1100px; padding-top:3.5rem}
        .stButton button, .stFormSubmitButton button{min-height:64px; font-size:1.05rem; font-weight:600}
        [class*="st-key-tile_"] button{height:260px; font-size:1.35rem; border-radius:8px;
            box-shadow:0 0 2px rgba(0,0,0,.12), 0 4px 8px rgba(0,0,0,.14)}
        [class*="st-key-tile_"] button p{font-size:1.35rem}
        [data-testid="stTextInputRootElement"], [data-baseweb="select"] > div{min-height:56px}
        [data-testid="stTextInputRootElement"] input{font-size:1.15rem}
        [data-testid="stButtonGroup"] button{min-height:56px; padding:0 1.1rem; font-size:1rem}
        .codigo-grande{font-size:5rem; font-weight:700; letter-spacing:.08em; color:#0F6CBD; line-height:1.1; margin:.4rem 0}
        </style>""",
        unsafe_allow_html=True,
    )
