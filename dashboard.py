import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime

# --- KURUMSAL AYARLAR ---
st.set_page_config(page_title="Lemniscate Finance Terminal", layout="wide")

# --- 1. VERİTABANI ALTYAPISI ---
def init_db():
    conn = sqlite3.connect('borsa_analiz.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analizler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            hisse TEXT,
            skor REAL,
            fiyat REAL,
            teknik_stop REAL,
            potansiyel TEXT
        )
    ''')
    conn.commit()
    return conn

# --- 2. ANALİZ MOTORU (KODUNUN BİREBİR AYNISI) ---
def analyze_stock(data):
    if len(data) < 50: return 0.0, 0.0
    score = 0.0
    try:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        close, high, low, vol = data["Close"], data["High"], data["Low"], data["Volume"]
        
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        if close.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1]: score += 1.5
        elif close.iloc[-1] > ema20.iloc[-1]: score += 1.0

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_val = (100 - (100 / (1 + rs))).iloc[-1]
        if 45 < rsi_val < 65: score += 1.0
        elif rsi_val <= 45: score += 0.5

        macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]: score += 1.0

        low_14, high_14 = low.tail(14).min(), high.tail(14).max()
        stoch = (close.iloc[-1] - low_14) / (high_14 - low_14) * 100 if high_14 != low_14 else 50
        if stoch < 20: score += 0.5

        sma20 = close.rolling(20).mean()
        if close.iloc[-1] > sma20.iloc[-1]: score += 0.5

        tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
        if tr.ewm(span=14).mean().iloc[-1] > 0: score += 0.5

        obv = (np.sign(close.diff().fillna(0)) * vol).cumsum()
        if obv.iloc[-1] > obv.iloc[-2]: score += 0.5
        if vol.tail(5).mean() > vol.tail(20).mean() * 1.5: score += 0.5

        atr = tr.rolling(14).mean().iloc[-1]
        stop_loss = close.iloc[-1] - (atr * 2) if not np.isnan(atr) else 0

        recent_high, recent_low = high.tail(50).max(), low.tail(50).min()
        diff = recent_high - recent_low
        if close.iloc[-1] > (recent_high - 0.382 * diff): score += 1.0

        return round(float(score), 2), round(float(stop_loss), 2)
    except:
        return 0.0, 0.0

# --- 3. ANALİZİ TETİKLEYEN ANA FONKSİYON ---
def piyasayi_analiz_et():
    tickers = [
        "A1CAP.IS","A1YEN.IS","ACSEL.IS","ADEL.IS","ADESE.IS","ADGYO.IS","AEFES.IS","AFYON.IS","AGESA.IS","AGHOL.IS",
        "AGROT.IS","AGYO.IS","AHGAZ.IS","AHSGY.IS","AKBNK.IS","AKCNS.IS","AKENR.IS","AKFGY.IS","AKFIS.IS","AKFYE.IS",
        "AKGRT.IS","AKHAN.IS","AKMGY.IS","AKSA.IS","AKSEN.IS","AKSGY.IS","AKSUE.IS","AKYHO.IS","ALARK.IS","ALBRK.IS",
        "ALCAR.IS","ALCTL.IS","ALFAS.IS","ALGYO.IS","ALKA.IS","ALKIM.IS","ALKLC.IS","ALTNY.IS","ALVES.IS","ANELE.IS",
        "ANGEN.IS","ANHYT.IS","ANSGR.IS","APMDL.IS","ARASE.IS","ARCLK.IS","ARDYZ.IS","ARENA.IS","ARFYE.IS","ARMGD.IS",
        "ARSAN.IS","ARTMS.IS","ARZUM.IS","ASELS.IS","ASGYO.IS","ASTOR.IS","ASUZU.IS","ATAGY.IS","ATAKP.IS","ATATP.IS",
        "ATEKS.IS","ATLAS.IS","ATSYH.IS","AVGYO.IS","AVHOL.IS","AVOD.IS","AVPGY.IS","AVTUR.IS","AYCES.IS","AYDEM.IS",
        "AYEN.IS","AYES.IS","AYGAZ.IS","AZTEK.IS","BAGFS.IS","BAHKM.IS","BAKAB.IS","BALAT.IS","BALSU.IS","BANVT.IS",
        "BARMA.IS","BASCM.IS","BASGZ.IS","BAYRK.IS","BEGYO.IS","BERA.IS","BESLR.IS","BESTE.IS","BEYAZ.IS","BFREN.IS",
        "BIENY.IS","BIGCH.IS","BIGEN.IS","BIGTK.IS","BIMAS.IS","BINBN.IS","BINHO.IS","BIOEN.IS","BIZIM.IS","BJKAS.IS",
        "BLCYT.IS","BLUME.IS","BMSCH.IS","BMSTL.IS","BNTAS.IS","BOBET.IS","BORLS.IS","BORSK.IS","BOSSA.IS","BRISA.IS",
        "BRKO.IS","BRKSN.IS","BRKVY.IS","BRLSM.IS","BRMEN.IS","BRSAN.IS","BRYAT.IS","BSOKE.IS","BTCIM.IS","BUCIM.IS",
        "BULGS.IS","BURCE.IS","BURVA.IS","BVSAN.IS","BYDNR.IS","CANTE.IS","CASA.IS","CATES.IS","CCOLA.IS","CELHA.IS",
        "CEMAS.IS","CEMTS.IS","CEMZY.IS","CEOEM.IS","CGCAM.IS","CIMSA.IS","CLEBI.IS","CMBTN.IS","CMENT.IS","CONSE.IS",
        "COSMO.IS","CRDFA.IS","CRFSA.IS","CUSAN.IS","CVKMD.IS","CWENE.IS","DAGI.IS","DAPGM.IS","DARDL.IS","DCTTR.IS",
        "DENGE.IS","DERHL.IS","DERIM.IS","DESA.IS","DESPC.IS","DEVA.IS","DGATE.IS","DGGYO.IS","DGNMO.IS","DIRIT.IS",
        "DITAS.IS","DMRGD.IS","DMSAS.IS","DNISI.IS","DOAS.IS","DOCO.IS","DOFER.IS","DOFRB.IS","DOGUB.IS","DOHOL.IS",
        "DOKTA.IS","DSTKF.IS","DUNYH.IS","DURDO.IS","DURKN.IS","DYOBY.IS","DZGYO.IS","EBEBK.IS","ECILC.IS","ECOGR.IS",
        "ECZYT.IS","EDATA.IS","EDIP.IS","EFOR.IS","EGEEN.IS","EGEGY.IS","EGEPO.IS","EGGUB.IS","EGPRO.IS","EGSER.IS",
        "EKGYO.IS","EKIZ.IS","EKOS.IS","EKSUN.IS","ELITE.IS","EMKEL.IS","EMNIS.IS","ENDAE.IS","ENERY.IS","ENJSA.IS",
        "ENKAI.IS","ENSRI.IS","ENTRA.IS","EPLAS.IS","ERBOS.IS","ERCB.IS","EREGL.IS","ERSU.IS","ESCAR.IS","ESCOM.IS",
        "ESEN.IS","ETILR.IS","ETYAT.IS","EUHOL.IS","EUKYO.IS","EUPWR.IS","EUREN.IS","EUYO.IS","EYGYO.IS","FADE.IS",
        "FENER.IS","FLAP.IS","FMIZP.IS","FONET.IS","FORMT.IS","FORTE.IS","FRIGO.IS","FRMPL.IS","FROTO.IS","FZLGY.IS",
        "GARAN.IS","GARFA.IS","GATEG.IS","GEDIK.IS","GEDZA.IS","GENIL.IS","GENTS.IS","GEREL.IS","GESAN.IS","GIPTA.IS",
        "GLBMD.IS","GLCVY.IS","GLRMK.IS","GLRYH.IS","GLYHO.IS","GMSTR.IS","GMTAS.IS","GOKNR.IS","GOLTS.IS","GOODY.IS",
        "GOZDE.IS","GRNYO.IS","GRSEL.IS","GRTHO.IS","GSDDE.IS","GSDHO.IS","GSRAY.IS","GUBRF.IS","GUNDG.IS","GWIND.IS",
        "GZNMI.IS","HALKB.IS","HATEK.IS","HATSN.IS","HDFGS.IS","HEDEF.IS","HEKTS.IS","HKTM.IS","HLGYO.IS","HOROZ.IS",
        "HRKET.IS","HTTBT.IS","HUBVC.IS","HUNER.IS","HURGZ.IS","ICBCT.IS","ICUGS.IS","IDGYO.IS","IEYHO.IS","IHAAS.IS",
        "IHEVA.IS","IHGZT.IS","IHLAS.IS","IHLGM.IS","IHYAY.IS","IMASM.IS","INDES.IS","INFO.IS","INGRM.IS","INTEK.IS",
        "INTEM.IS","INVEO.IS","INVES.IS","ISATR.IS","ISBIR.IS","ISBTR.IS","ISCTR.IS","ISDMR.IS","ISFIN.IS","ISGSY.IS",
        "ISGYO.IS","ISKPL.IS","ISKUR.IS","ISMEN.IS","ISSEN.IS","ISYAT.IS","IZENR.IS","IZFAS.IS","IZINV.IS","IZMDC.IS",
        "JANTS.IS","KAPLM.IS","KAREL.IS","KARSN.IS","KARTN.IS","KATMR.IS","KAYSE.IS","KBORU.IS","KCAER.IS","KCHOL.IS",
        "KENT.IS","KERVN.IS","KFEIN.IS","KGYO.IS","KIMMR.IS","KLGYO.IS","KLKIM.IS","KLMSN.IS","KLNMA.IS","KLRHO.IS",
        "KLSER.IS","KLSYN.IS","KLYPV.IS","KMPUR.IS","KNFRT.IS","KOCMT.IS","KONKA.IS","KONTR.IS","KONYA.IS","KOPOL.IS",
        "KORDS.IS","KOTON.IS","KRDMA.IS","KRDMB.IS","KRDMD.IS","KRGYO.IS","KRONT.IS","KRPLS.IS","KRSTL.IS","KRTEK.IS",
        "KRVGD.IS","KSTUR.IS","KTLEV.IS","KTSKR.IS","KUTPO.IS","KUVVA.IS","KUYAS.IS","KZBGY.IS","KZGYO.IS","LIDER.IS",
        "LIDFA.IS","LILAK.IS","LINK.IS","LKMNH.IS","LMKDC.IS","LOGO.IS","LRSHO.IS","LUKSK.IS","LYDHO.IS","LYDYE.IS",
        "MAALT.IS","MACKO.IS","MAGEN.IS","MAKIM.IS","MAKTK.IS","MANAS.IS","MARBL.IS","MARKA.IS","MARMR.IS","MARTI.IS",
        "MAVI.IS","MEDTR.IS","MEGAP.IS","MEGMT.IS","MEKAG.IS","MEPET.IS","MERCN.IS","MERIT.IS","MERKO.IS","METRO.IS",
        "MEYSU.IS","MGROS.IS","MHRGY.IS","MIATK.IS","MMCAS.IS","MNDRS.IS","MNDTR.IS","MOBTL.IS","MOGAN.IS","MOPAS.IS",
        "MPARK.IS","MRGYO.IS","MRSHL.IS","MSGYO.IS","MTRKS.IS","MTRYO.IS","MZHLD.IS","NATEN.IS","NETAS.IS","NETCD.IS",
        "NIBAS.IS","NTGAZ.IS","NTHOL.IS","NUGYO.IS","NUHCM.IS","OBAMS.IS","OBASE.IS","ODAS.IS","ODINE.IS","OFSYM.IS",
        "ONCSM.IS","ONRYT.IS","OPK30.IS","OPX30.IS","ORCAY.IS","ORGE.IS","ORMA.IS","OSMEN.IS","OSTIM.IS","OTKAR.IS",
        "OTTO.IS","OYAKC.IS","OYAYO.IS","OYLUM.IS","OYYAT.IS","OZATD.IS","OZGYO.IS","OZKGY.IS","OZRDN.IS","OZSUB.IS",
        "OZYSR.IS","PAGYO.IS","PAHOL.IS","PAMEL.IS","PAPIL.IS","PARSN.IS","PASEU.IS","PATEK.IS","PCILT.IS","PEKGY.IS",
        "PENGD.IS","PENTA.IS","PETKM.IS","PETUN.IS","PGSUS.IS","PINSU.IS","PKART.IS","PKENT.IS","PLTUR.IS","PNLSN.IS",
        "PNSUT.IS","POLHO.IS","POLTK.IS","PRDGS.IS","PRKAB.IS","PRKME.IS","PRZMA.IS","PSDTC.IS","PSGYO.IS","QNBFK.IS",
        "QNBTR.IS","QTEMZ.IS","QUAGR.IS","RALYH.IS","RAYSG.IS","REEDR.IS","RGYAS.IS","RNPOL.IS","RODRG.IS","RTALB.IS",
        "RUBNS.IS","RUZYE.IS","RYGYO.IS","RYSAS.IS","SAFKR.IS","SAHOL.IS","SAMAT.IS","SANEL.IS","SANFM.IS","SANKO.IS",
        "SARKY.IS","SASA.IS","SAYAS.IS","SDTTR.IS","SEGMN.IS","SEGYO.IS","SEKFK.IS","SEKUR.IS","SELEC.IS","SELVA.IS",
        "SERNT.IS","SEYKM.IS","SILVR.IS","SISE.IS","SKBNK.IS","SKTAS.IS","SKYLP.IS","SKYMD.IS","SMART.IS","SMRTG.IS",
        "SMRVA.IS","SNGYO.IS","SNICA.IS","SNPAM.IS","SODSN.IS","SOKE.IS","SOKM.IS","SONME.IS","SRVGY.IS","SUMAS.IS",
        "SUNTK.IS","SURGY.IS","SUWEN.IS","TABGD.IS","TARKM.IS","TATEN.IS","TATGD.IS","TAVHL.IS","TBORG.IS","TCELL.IS",
        "TCKRC.IS","TDGYO.IS","TEHOL.IS","TEKTU.IS","TERA.IS","TEZOL.IS","TGSAS.IS","THYAO.IS","TKFEN.IS","TKNSA.IS",
        "TLMAN.IS","TMPOL.IS","TMSN.IS","TNZTP.IS","TOASO.IS","TRALT.IS","TRCAS.IS","TRENJ.IS","TRGYO.IS","TRHOL.IS",
        "TRILC.IS","TRMET.IS","TSGYO.IS","TSKB.IS","TSPOR.IS","TTKOM.IS","TTRAK.IS","TUCLK.IS","TUKAS.IS","TUPRS.IS",
        "TUREX.IS","TURGG.IS","TURSG.IS","UCAYM.IS","UFUK.IS","ULAS.IS","ULKER.IS","ULUFA.IS","ULUSE.IS","ULUUN.IS",
        "UNLU.IS","USAK.IS","USDTR.IS","VAKBN.IS","VAKFA.IS","VAKFN.IS","VAKKO.IS","VANGD.IS","VBTYZ.IS","VERTU.IS",
        "VERUS.IS","VESBE.IS","VESTL.IS","VKFYO.IS","VKGYO.IS","VKING.IS","VRGYO.IS","VSNMD.IS","YAPRK.IS","YATAS.IS",
        "YAYLA.IS","YBTAS.IS","YEOTK.IS","YESIL.IS","YGGYO.IS","YIGIT.IS","YKBNK.IS","YKSLN.IS","YONGA.IS","YUNSA.IS",
        "YYAPI.IS","YYLGD.IS","ZEDUR.IS","ZERGY.IS","ZGYO.IS","ZOREN.IS","ZRGYO.IS"
    ]
    
    conn = init_db()
    tarih_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    with st.status("♾️ Lemniscate Engine: Piyasa Taranıyor...", expanded=True) as status:
        data_all = yf.download(tickers, period="150d", group_by='ticker', progress=False)
        all_results = []
        
        for ticker in tickers:
            try:
                df = data_all[ticker].copy().dropna()
                if df.empty: continue
                skor, stop = analyze_stock(df)
                fiyat = df['Close'].iloc[-1]
                all_results.append((tarih_str, ticker, skor, round(float(fiyat), 2), stop, "Yüksek" if skor >= 5.5 else "Orta"))
            except: continue

        if all_results:
            cursor = conn.cursor()
            cursor.executemany('INSERT INTO analizler (tarih, hisse, skor, fiyat, teknik_stop, potansiyel) VALUES (?,?,?,?,?,?)', all_results)
            conn.commit()
            status.update(label=f"✅ Başarılı: {len(all_results)} Hisse Mühürlendi!", state="complete", expanded=False)
    conn.close()

# --- 4. VERİTABANI OKUMA ---
def veritabanindan_getir(hisse_kodu=None):
    conn = init_db()
    if hisse_kodu:
        kodu = hisse_kodu.upper() if ".IS" in hisse_kodu.upper() else f"{hisse_kodu.upper()}.IS"
        query = f"SELECT * FROM analizler WHERE hisse = '{kodu}' ORDER BY id DESC LIMIT 1"
    else:
        query = "SELECT * FROM analizler WHERE tarih = (SELECT MAX(tarih) FROM analizler) ORDER BY skor DESC LIMIT 10"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- 5. ARAYÜZ AKIŞI ---

# YASAL UYARI
st.error("⚠️ **YATIRIM TAVSİYESİ DEĞİLDİR:** Bu terminalde paylaşılan veriler ve skorlar tamamen algoritma tarafından üretilmiştir. Yatırım kararlarınızı kendi araştırmalarınızla veriniz.")

st.title("♾️ Lemniscate Finance | Yatırım Terminali")

# SIDEBAR
st.sidebar.title("♾️ Lemniscate Finance")
st.sidebar.warning("📢 **UYARI:** Yatırım Tavsiyesi Değildir.")
st.sidebar.divider()

if st.sidebar.button("🔄 PİYASAYI ANALİZ ET", use_container_width=True):
    piyasayi_analiz_et()
    st.rerun()

st.sidebar.subheader("🔍 Hisse Sorgu")
if 'sorgulanan_hisse' not in st.session_state:
    st.session_state.sorgulanan_hisse = None

input_hisse = st.sidebar.text_input("Hisse Kodu (Örn: THYAO)", "").upper()
c1, c2 = st.sidebar.columns(2)
if c1.button("Analiz Getir"): st.session_state.sorgulanan_hisse = input_hisse
if c2.button("Ana Sayfa"): 
    st.session_state.sorgulanan_hisse = None
    st.rerun()

# ANA EKRAN MANTIĞI
if st.session_state.sorgulanan_hisse:
    sonuc_df = veritabanindan_getir(st.session_state.sorgulanan_hisse)
    if not sonuc_df.empty:
        res = sonuc_df.iloc[0]
        st.header(f"📊 {res['hisse']} Detaylı Raporu")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Robot Skoru", f"{res['skor']} / 10")
        m2.metric("Güncel Fiyat", f"{res['fiyat']} TL")
        m3.metric("Teknik Stop", f"{res['teknik_stop']} TL")
        m4.metric("Sinyal Gücü", res['potansiyel'])
        
        st.divider()
        st.subheader("📈 Teknik Görünüm")
        df_plot = yf.download(res['hisse'], period="1mo", progress=False)
        if not df_plot.empty:
            if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
            fig = go.Figure(data=[go.Scatter(x=df_plot.index, y=df_plot['Close'], line=dict(color='#00d1ff'))])
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"'{st.session_state.sorgulanan_hisse}' bulunamadı. Lütfen önce 'Piyasayı Analiz Et' butonuna basın.")
else:
    st.subheader("🏆 Günün En Güçlüleri (Top 10)")
    top_10 = veritabanindan_getir()
    if not top_10.empty:
        st.dataframe(top_10[['hisse', 'skor', 'fiyat', 'potansiyel', 'tarih']], use_container_width=True, hide_index=True)
        st.bar_chart(data=top_10, x='hisse', y='skor', color="#00d1ff")
    else:
        st.info("Henüz analiz verisi yok. Sol taraftaki 'Piyasayı Analiz Et' butonuna basarak taramayı başlatın.")

st.sidebar.caption(f"Lemniscate Finance © {datetime.now().year}")