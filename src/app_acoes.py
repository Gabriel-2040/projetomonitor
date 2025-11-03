import os
import sys
import subprocess

# Se o script estiver sendo executado como um executável (.exe)
if getattr(sys, 'frozen', False):
    # Caminho da pasta onde o .exe está
    base_path = os.path.dirname(sys.executable)

    # Caminho real do script Python original
    script_path = os.path.join(base_path, 'app_acoes.py')

    # Executa o Streamlit e abre o app
    subprocess.Popen(['streamlit', 'run', script_path, '--server.headless', 'true'])
    sys.exit()

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Analisador de Ações com Dividendos",
    page_icon="📈",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .alert-box {
        padding: 20px;
        background-color: #ffcccc;
        border: 2px solid #ff0000;
        border-radius: 10px;
        margin: 10px 0;
    }
    .good-price {
        background-color: #ccffcc;
        border: 2px solid #00ff00;
    }
    .info-box {
        padding: 15px;
        background-color: #e6f3ff;
        border: 1px solid #0077cc;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================
# CLASSE PRINCIPAL
# ==============================
class AnalisadorAcoes:
    def __init__(self):
        self.acoes_dividendos = {
            'Setor de Energia': {
                'EGIE3.SA': 'Engie Brasil',
                'CPFE3.SA': 'CPFL Energia',
                'EQTL3.SA': 'Equatorial Energia',
                'TAEE4.SA': 'Taesa'
            },
            'Setor de Saneamento': {
                'SBSP3.SA': 'Sabesp',
                'SAPR4.SA': 'Sanepar',
                'CSMG3.SA': 'Copasa'
            },
            'Setor Financeiro': {
                'BBAS3.SA': 'Banco do Brasil',
                'ITUB4.SA': 'Itaú Unibanco',
                'BBDC4.SA': 'Bradesco'
            },
            'Outros Setores': {
                'VALE3.SA': 'Vale',
                'VIVT3.SA': 'Telefônica Brasil'
            }
        }

    def obter_dados_acao(self, ticker, periodo="1y"):
        """Obtém dados históricos usando .history() (mais confiável para ações BR)"""
        try:
            acao = yf.Ticker(ticker)
            dados = acao.history(period=periodo, interval="1d")
            if dados.empty:
                st.warning(f"Nenhum dado encontrado para {ticker}. Pode estar sem negociação recente.")
                return None, acao
            return dados, acao
        except Exception as e:
            st.error(f"Erro ao obter dados para {ticker}: {e}")
            return None, None

    def analisar_historico(self, dados, ticker):
        """Gera estatísticas básicas de preço"""
        if dados is None or dados.empty:
            return None

        analise = {
            'ticker': ticker,
            'preco_atual': dados['Close'][-1],
            'min_1ano': dados['Close'].min(),
            'max_1ano': dados['Close'].max(),
            'variacao_1ano': ((dados['Close'][-1] - dados['Close'][0]) / dados['Close'][0]) * 100
        }

        # Dados de 5 anos
        dados_5anos, _ = self.obter_dados_acao(ticker, "5y")
        if dados_5anos is not None and not dados_5anos.empty:
            analise['min_5anos'] = dados_5anos['Close'].min()
            analise['max_5anos'] = dados_5anos['Close'].max()
        else:
            analise['min_5anos'] = None
            analise['max_5anos'] = None

        return analise

    def criar_grafico_historico(self, dados, ticker):
        """Cria gráfico interativo com candles e média móvel"""
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(f'Histórico de Preços - {ticker}', 'Volume'),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=dados.index,
                open=dados['Open'],
                high=dados['High'],
                low=dados['Low'],
                close=dados['Close'],
                name='Preço'
            ),
            row=1, col=1
        )

        # Média móvel de 20 dias
        dados['MA20'] = dados['Close'].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=dados.index,
                y=dados['MA20'],
                name='Média Móvel 20 dias',
                line=dict(color='orange', width=2)
            ),
            row=1, col=1
        )

        # Volume
        fig.add_trace(
            go.Bar(
                x=dados.index,
                y=dados['Volume'],
                name='Volume',
                marker_color='lightblue'
            ),
            row=2, col=1
        )

        fig.update_layout(
            height=600,
            showlegend=True,
            xaxis_rangeslider_visible=False
        )
        return fig

    def verificar_alerta_preco(self, analise):
        """Verifica se preço está perto do mínimo anual"""
        if analise is None:
            return False, ""
        preco_atual = analise['preco_atual']
        min_ano = analise['min_1ano']
        distancia_min = ((preco_atual - min_ano) / min_ano) * 100

        if preco_atual <= min_ano:
            return True, "🚨 ALERTA CRÍTICO: Novo mínimo anual!"
        elif distancia_min <= 5:
            return True, f"⚠️ Preço próximo do mínimo anual ({distancia_min:.2f}% acima)"
        else:
            return False, f"✅ Preço está {distancia_min:.2f}% acima do mínimo anual"


# ==============================
# INTERFACE PRINCIPAL STREAMLIT
# ==============================
def main():

    analisador = AnalisadorAcoes()
    setor = st.sidebar.selectbox("Setor:", list(analisador.acoes_dividendos.keys()))
    acoes_setor = analisador.acoes_dividendos[setor]
    ticker = st.sidebar.selectbox(
        "Ação:",
        list(acoes_setor.keys()),
        format_func=lambda x: f"{acoes_setor[x]} ({x})"
    )
    st.title("📈 Analisador de Ações com Dividendos")
    st.title(f"Analisando {ticker}")
    st.markdown("---")
    # Sidebar
    st.sidebar.header("🔍 Seleção da Ação")
    
    
    
    periodo = st.sidebar.selectbox("Período:", ["1y", "6mo", "3mo", "1mo"], index=0)

    # Conteúdo principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.spinner("📡 Obtendo dados..."):
            dados, info = analisador.obter_dados_acao(ticker, periodo)
        if dados is not None and not dados.empty:
            analise = analisador.analisar_historico(dados, ticker)
            alerta, msg_alerta = analisador.verificar_alerta_preco(analise)

            # Exibe alerta
            if alerta:
                st.markdown(f'<div class="alert-box">{msg_alerta}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-box good-price">{msg_alerta}</div>', unsafe_allow_html=True)

            # Gráfico
            fig = analisador.criar_grafico_historico(dados, ticker)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Indicadores")
        if dados is not None and not dados.empty:
            st.metric("💵 Preço Atual", f"R$ {analise['preco_atual']:.2f}")
            st.metric("📉 Mínimo do Ano", f"R$ {analise['min_1ano']:.2f}")
            st.metric("📈 Máximo do Ano", f"R$ {analise['max_1ano']:.2f}")
            st.metric("📊 Variação Anual", f"{analise['variacao_1ano']:.2f}%")

            if analise['min_5anos'] is not None:
                st.markdown("---")
                st.metric("Mínimo 5 Anos", f"R$ {analise['min_5anos']:.2f}")
                st.metric("Máximo 5 Anos", f"R$ {analise['max_5anos']:.2f}")

    # Extras
    if dados is not None and not dados.empty:
        st.markdown("---")
        st.subheader("📋 Análise Técnica")
        col3, col4, col5 = st.columns(3)
        volatilidade = dados['Close'].pct_change().std() * (252 ** 0.5) * 100
        volume_medio = dados['Volume'].mean()
        variacao_dia = ((dados['Close'][-1] - dados['Open'][-1]) / dados['Open'][-1]) * 100
        col3.metric("Volatilidade", f"{volatilidade:.2f}%")
        col4.metric("Volume Médio", f"{volume_medio:,.0f}")
        col5.metric("Variação do Dia", f"{variacao_dia:.2f}%")


if __name__ == "__main__":
    main()
