import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# --- KURUMSAL AYARLAR ---
st.set_page_config(page_title="Lemniscate Finance Terminal", layout="wide")

# Veritabanı Fonksiyonu
def veritabanindan_getir(hisse_kodu=None):
    conn = sqlite3.connect('borsa_analiz.db')
    try:
        if hisse_kodu:
            # .IS eki kontrolü
            kodu = hisse_kodu.upper() if ".IS" in hisse_kodu.upper() else f"{hisse_kodu.upper()}.IS"
            query = f"SELECT * FROM analizler WHERE hisse = '{kodu}' ORDER BY id DESC LIMIT 1"
        else:
            # Robotun yaptığı en son taramanın top 10 listesi
            query = "SELECT * FROM analizler WHERE tarih = (SELECT MAX(tarih) FROM analizler) ORDER BY skor DESC LIMIT 10"
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# --- HAFIZA YÖNETİMİ ---
if 'sorgulanan_hisse' not in st.session_state:
    st.session_state.sorgulanan_hisse = None

# --- YAN PANEL (SIDEBAR) ---
st.sidebar.title("♾️ Lemniscate Finance")
st.sidebar.markdown("*Sonsuz Analiz, Kesin Karar*")
st.sidebar.success("🤖 Robot Modu: Aktif (09:30)")
st.sidebar.divider()

st.sidebar.subheader("🔍 Hisse Sorgu Terminali")
input_hisse = st.sidebar.text_input("Hisse Kodu (Örn: THYAO)", "").upper()

col_side1, col_side2 = st.sidebar.columns(2)
if col_side1.button("Analiz Getir"):
    st.session_state.sorgulanan_hisse = input_hisse

if col_side2.button("Ana Sayfa"):
    st.session_state.sorgulanan_hisse = None
    st.rerun()

# --- ANA SAYFA AKIŞI ---
st.title("♾️ Lemniscate Finance | Yatırım Terminali")

# DURUM 1: BİR HİSSE SORGULANDIĞINDA
if st.session_state.sorgulanan_hisse:
    sonuc_df = veritabanindan_getir(st.session_state.sorgulanan_hisse)
    
    if not sonuc_df.empty:
        res = sonuc_df.iloc[0]
        st.header(f"📊 {res['hisse']} Detaylı Raporu")
        
        # Metrik Kartları
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Robot Skoru", f"{res['skor']} / 10")
        c2.metric("Güncel Fiyat", f"{res['fiyat']} TL")
        c3.metric("Teknik Stop", f"{res['teknik_stop']} TL")
        c4.metric("Sinyal Gücü", res['potansiyel']) 
        
        st.divider()

        # Teknik Grafik Alanı
        st.subheader("📈 Teknik Görünüm (Canlı Veri)")
        zaman_araligi = st.radio("Periyot:", ["1 Hafta", "1 Ay", "6 Ay", "1 Yıl"], horizontal=True, key="zaman_secici")
        period_map = {"1 Hafta": "5d", "1 Ay": "1mo", "6 Ay": "6mo", "1 Yıl": "1y"}
        
        with st.spinner("Canlı grafik verileri çekiliyor..."):
            df_plot = yf.download(res['hisse'], period=period_map[zaman_araligi], progress=False)
            if not df_plot.empty:
                if isinstance(df_plot.columns, pd.MultiIndex):
                    df_plot.columns = df_plot.columns.get_level_values(0)

                # EMA Hesaplamaları
                df_plot['EMA20'] = df_plot['Close'].ewm(span=20, adjust=False).mean()
                df_plot['EMA50'] = df_plot['Close'].ewm(span=50, adjust=False).mean()

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], name='Fiyat', line=dict(color='#00d1ff', width=2.5)))
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name='EMA 20', line=dict(color='#ff9900', width=1.5, dash='dot')))
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], name='EMA 50', line=dict(color='#ff4b4b', width=1.5)))

                fig.update_layout(template="plotly_dark", hovermode="x unified", height=500, margin=dict(l=0, r=0, t=10, b=0),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                  xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.caption(f"Veritabanındaki son kayıt tarihi: {res['tarih']}")
            else:
                st.warning("Grafik verisi şu an çekilemiyor.")
    else:
        st.error(f"❌ '{st.session_state.sorgulanan_hisse}' veritabanında bulunamadı. Robotun tarama yapmasını bekleyin.")

# DURUM 2: ANA SAYFA (SORGULAMA YOKSA)
else:
    st.subheader("🏆 Lemniscate Top 10 | Günün En Güçlüleri")
    top_10_df = veritabanindan_getir()

    if not top_10_df.empty:
        # Görsel düzenleme
        display_df = top_10_df[['hisse', 'skor', 'fiyat', 'teknik_stop', 'potansiyel', 'tarih']].copy()
        display_df.columns = ['Hisse', 'Skor', 'Fiyat', 'Stop', 'Sinyal', 'Tarama Tarihi']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Skor Dağılım Grafiği
        st.bar_chart(data=top_10_df, x='hisse', y='skor', color="#00d1ff")
        st.info("Yukarıdaki liste robotun sabah 09:30'da yaptığı analiz sonuçlarına göre puanlanmıştır.")
    else:
        st.info("Henüz analiz verisi bulunamadı. Lütfen robotun (`robot.py`) çalışıp çalışmadığını kontrol edin.")

st.sidebar.caption(f"Lemniscate Finance © {datetime.now().year}")