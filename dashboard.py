import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime

# --- KURUMSAL AYARLAR ---
st.set_page_config(page_title="Lemniscate Finance Terminal", layout="wide")

# --- 1. VERİTABANI ALTYAPISI (HATA KORUMALI) ---
def init_db():
    conn = sqlite3.connect('borsa_analiz.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Analizler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analizler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT, hisse TEXT, skor REAL, fiyat REAL, teknik_stop REAL, potansiyel TEXT
        )
    ''')
    
    # 2. Performans Takip Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kayit_tarihi TEXT, 
            hafta_no INTEGER,
            hisse TEXT, 
            baslangic_fiyati REAL,
            guncel_fiyat REAL
        )
    ''')

    # --- SÜTUN KONTROLÜ (Hata Alan Yer İçin Otomatik Düzeltme) ---
    cursor.execute("PRAGMA table_info(performans)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'hafta_no' not in columns:
        cursor.execute("ALTER TABLE performans ADD COLUMN hafta_no INTEGER")
    if 'guncel_fiyat' not in columns:
        cursor.execute("ALTER TABLE performans ADD COLUMN guncel_fiyat REAL")
        
    conn.commit()
    return conn

# --- 2. LEMNISCATE ANALİZ MOTORU ---
def analyze_stock(data):
    if len(data) < 50: return 0.0, 0.0
    try:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        close, high, low, vol = data["Close"], data["High"], data["Low"], data["Volume"]
        score = 0.0
        
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

        macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]: score += 1.0

        tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        stop_loss = close.iloc[-1] - (atr * 2) if not np.isnan(atr) else 0

        recent_high, recent_low = high.tail(50).max(), low.tail(50).min()
        if close.iloc[-1] > (recent_high - 0.382 * (recent_high - recent_low)): score += 1.0

        return round(float(score), 2), round(float(stop_loss), 2)
    except: return 0.0, 0.0

# --- 3. PİYASA TARAMA VE HAFTALIK KAYIT ---
def piyasayi_analiz_et():
    # Devasa hisse listen burada kalıyor, kısalttım (sen kendininkini ekle)
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
    cursor = conn.cursor()
    simdi = datetime.now()
    tarih_str = simdi.strftime('%Y-%m-%d %H:%M')
    hafta_no = simdi.isocalendar()[1]
    
    with st.status("♾️ Engine: Piyasa Taranıyor...", expanded=True) as status:
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
            cursor.executemany('INSERT INTO analizler (tarih, hisse, skor, fiyat, teknik_stop, potansiyel) VALUES (?,?,?,?,?,?)', all_results)
            
            # HAFTALIK SABİTLEME: Eğer bu hafta kayıt yoksa Top 10 mühürle
            cursor.execute("SELECT id FROM performans WHERE hafta_no = ?", (hafta_no,))
            if cursor.fetchone() is None:
                top_10 = sorted(all_results, key=lambda x: x[2], reverse=True)[:10]
                perf_list = [(tarih_str, hafta_no, t[1], t[3], t[3]) for t in top_10]
                cursor.executemany('INSERT INTO performans (kayit_tarihi, hafta_no, hisse, baslangic_fiyati, guncel_fiyat) VALUES (?,?,?,?,?)', perf_list)
            
            conn.commit()
            status.update(label=f"✅ Başarılı: {len(all_results)} Analiz Kaydedildi!", state="complete", expanded=False)
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

# --- 5. ARAYÜZ VE MENÜ ---
st.error("⚠️ **YATIRIM TAVSİYESİ DEĞİLDİR:** Bu terminaldeki tüm veriler algoritma üretimidir.")

st.sidebar.title("♾️ Lemniscate Finance")
menu_secim = st.sidebar.radio("Görünüm Seçin:", ["📊 Canlı Terminal", "📈 Haftalık Performans"])
st.sidebar.divider()

if menu_secim == "📊 Canlı Terminal":
    st.title("♾️ Lemniscate Finance | Terminal")
    if st.sidebar.button("🔄 PİYASAYI ANALİZ ET", use_container_width=True):
        piyasayi_analiz_et()
        st.rerun()

    input_hisse = st.sidebar.text_input("Hisse Kodu (Örn: THYAO)", "").upper()
    if st.sidebar.button("Analiz Getir"): st.session_state.sorgulanan_hisse = input_hisse

    # Ana Sayfa - Top 10
    top_10 = veritabanindan_getir()
    if not top_10.empty:
        st.subheader("🏆 Günün Liderleri (Top 10)")
        st.dataframe(top_10[['hisse', 'skor', 'fiyat', 'tarih']], use_container_width=True, hide_index=True)
        st.bar_chart(data=top_10, x='hisse', y='skor', color="#00d1ff")

elif menu_secim == "📈 Haftalık Performans":
    st.title("📈 Haftalık Performans Takibi")
    hafta_no = datetime.now().isocalendar()[1]
    st.info(f"📅 Şu an {hafta_no}. haftadasınız. Liste her hafta başı ilk analizde mühürlenir.")
    
    conn = init_db()
    # SQL hatasını önlemek için güvenli sorgulama
    try:
        perf_df = pd.read_sql_query("SELECT * FROM performans WHERE hafta_no = ?", conn, params=(hafta_no,))
        
        if not perf_df.empty:
            if st.button("🚀 Canlı Fiyatları Güncelle", use_container_width=True):
                with st.spinner("Fiyatlar çekiliyor..."):
                    cursor = conn.cursor()
                    for idx, row in perf_df.iterrows():
                        live = yf.download(row['hisse'], period="5d", progress=False)
                        if not live.empty:
                            if isinstance(live.columns, pd.MultiIndex): live.columns = live.columns.get_level_values(0)
                            current_p = round(float(live['Close'].iloc[-1]), 2)
                            cursor.execute("UPDATE performans SET guncel_fiyat = ? WHERE id = ?", (current_p, row['id']))
                    conn.commit()
                    st.rerun()

            cols = st.columns(2)
            for i, (idx, row) in enumerate(perf_df.iterrows()):
                with cols[i % 2].container(border=True):
                    baslangic, guncel = row['baslangic_fiyati'], row['guncel_fiyat']
                    fark = ((guncel - baslangic) / baslangic) * 100
                    st.subheader(f"📍 {row['hisse']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Giriş (Pzt)", f"{baslangic} TL")
                    c2.metric("Güncel", f"{guncel} TL")
                    c3.metric("Değişim", f"%{round(fark, 2)}", delta=f"{round(fark, 2)}%")
        else:
            st.warning("Bu hafta için mühürlenmiş liste yok. Analiz başlatın.")
    except Exception as e:
        st.error(f"Veritabanı Yapılandırma Hatası: {e}. Lütfen analiz yapın.")
    conn.close()

st.sidebar.caption(f"Lemniscate Finance © {datetime.now().year}")