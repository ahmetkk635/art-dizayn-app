import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="ART DİZAYN Panel", page_icon="🏗️", layout="wide")

# Veritabanı Entegrasyonu
conn = sqlite3.connect('art_dizayn.db', check_same_thread=False)
c = conn.cursor()

# Tabloların Oluşturulması
c.execute('''CREATE TABLE IF NOT EXISTS kasa 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, tur TEXT, aciklama TEXT, tutar REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS cariler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, isim TEXT, tur TEXT, tutar REAL, aciklama TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS malzemeler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, ad TEXT, birim TEXT, fiyat REAL)''')
conn.commit()

st.title("🏗️ ART DİZAYN - Bütünleşik Yönetim Paneli")

# Mobil ve Masaüstü Sekme Menüsü
tab1, tab2, tab3, tab4 = st.tabs(["💰 Kasa Defteri", "📊 Alacak / Borç", "📦 Malzeme & Birim Fiyat", "📝 Teklif Oluştur"])

# ---------------------------------------------------------
# 1. KASA DEFTERİ
# ---------------------------------------------------------
with tab1:
    st.subheader("💰 Günlük Kasa Hareketleri")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Yeni İşlem Ekle**")
        k_tarih = st.date_input("İşlem Tarihi")
        k_tur = st.selectbox("İşlem Türü", ["Gelir (Tahsilat)", "Gider (Harcama)"])
        k_aciklama = st.text_input("Açıklama (Örn: Müşteri kapora / Malzeme alımı)")
        k_tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)
        
        if st.button("💾 Kasaya İşle", use_container_width=True):
            c.execute("INSERT INTO kasa (tarih, tur, aciklama, tutar) VALUES (?, ?, ?, ?)",
                      (str(k_tarih), k_tur, k_aciklama, k_tutar))
            conn.commit()
            st.success("Kasa hareketi kaydedildi.")

    with col2:
        st.write("**Kasa Özet ve Döküm**")
        df_kasa = pd.read_sql_query("SELECT * FROM kasa ORDER BY id DESC", conn)
        
        gelir = df_kasa[df_kasa['tur'] == "Gelir (Tahsilat)"]['tutar'].sum()
        gider = df_kasa[df_kasa['tur'] == "Gider (Harcama)"]['tutar'].sum()
        bakiye = gelir - gider
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Gelir", f"{gelir:,.2f} TL")
        m2.metric("Toplam Gider", f"{gider:,.2f} TL")
        m3.metric("Net Kasa Bakiye", f"{bakiye:,.2f} TL")
        
        st.dataframe(df_kasa, use_container_width=True)

# ---------------------------------------------------------
# 2. ALACAK & BORÇ TAKİBİ
# ---------------------------------------------------------
with tab2:
    st.subheader("📊 Cari Alacak / Borç Durumları")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.write("**Yeni Cari Kaydı**")
        c_isim = st.text_input("Müşteri / Tedarikçi Adı")
        c_tur = st.selectbox("Durum Türü", ["Alacak (Müşteriden)", "Borç (Tedarikçiye)"])
        c_tutar = st.number_input("Bakiye Tutarı (TL)", min_value=0.0, step=500.0)
        c_aciklama = st.text_input("İş / Proje Açıklaması")
        
        if st.button("💾 Cari Kaydet", use_container_width=True):
            c.execute("INSERT INTO cariler (isim, tur, tutar, aciklama) VALUES (?, ?, ?, ?)",
                      (c_isim, c_tur, c_tutar, c_aciklama))
            conn.commit()
            st.success("Cari kayıt eklendi.")

    with col_b:
        st.write("**Cari Bakiye Listesi**")
        df_cari = pd.read_sql_query("SELECT * FROM cariler", conn)
        
        toplam_alacak = df_cari[df_cari['tur'] == "Alacak (Müşteriden)"]['tutar'].sum()
        toplam_borc = df_cari[df_cari['tur'] == "Borç (Tedarikçiye)"]['tutar'].sum()
        
        ca1, ca2 = st.columns(2)
        ca1.metric("Toplam Alacaklarımız", f"{toplam_alacak:,.2f} TL")
        ca2.metric("Toplam Borçlarımız", f"{toplam_borc:,.2f} TL")
        
        st.dataframe(df_cari, use_container_width=True)

# ---------------------------------------------------------
# 3. MALZEME LİSTESİ VE BİRİM FİYATLARI
# ---------------------------------------------------------
with tab3:
    st.subheader("📦 Malzeme Listesi ve Birim Fiyat Kataloğu")
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.write("**Yeni Malzeme / Fiyat Tanımla**")
        m_kod = st.text_input("Ürün Kodu", "PNC-01")
        m_ad = st.text_input("Malzeme / Ürün Adı", "Özel Ölçü PVC Pencere (Adet)")
        m_birim = st.selectbox("Birim", ["Adet", "m²", "Metre", "Takım"])
        m_fiyat = st.number_input("Birim Satış Fiyatı (TL)", value=10000.0, step=250.0)
        
        if st.button("💾 Malzemeyi Kaydet", use_container_width=True):
            c.execute("INSERT INTO malzemeler (kod, ad, birim, fiyat) VALUES (?, ?, ?, ?)",
                      (m_kod, m_ad, m_birim, m_fiyat))
            conn.commit()
            st.success("Malzeme kataloğa eklendi.")

    with col_m2:
        st.write("**Güncel Fiyat Kataloğu**")
        df_malzeme = pd.read_sql_query("SELECT * FROM malzemeler", conn)
        
        # Örnek hazır veri yoksa gösterim amaçlı varsayılan tablo
        if df_malzeme.empty:
            df_malzeme = pd.DataFrame([
                {"kod": "PNC-01", "ad": "Standart PVC Pencere", "birim": "Adet", "fiyat": 10000.0},
                {"kod": "CAM-02", "ad": "Isıcamlı Cam Balkon Sistemleri", "birim": "m²", "fiyat": 3200.0},
                {"kod": "ALM-03", "ad": "Alüminyum Korkuluk / Küpeşte", "birim": "Metre", "fiyat": 1800.0}
            ])
            
        st.dataframe(df_malzeme, use_container_width=True)

# ---------------------------------------------------------
# 4. TEKLİF OLUŞTURMA
# ---------------------------------------------------------
with tab4:
    st.subheader("📝 Hazır Malzemelerle Teklif Oluştur")
    st.info("Katalogdaki birim fiyatlar (Örn: 1 Adet Pencere = 10.000 TL) üzerinden otomatik teklif hazırlayabilirsiniz.")
    
    # Katalog verisini çek
    df_kat = pd.read_sql_query("SELECT ad, birim, fiyat FROM malzemeler", conn)
    
    if not df_kat.empty:
        st.write("**Hazır Ürün Seçimi**")
        secilen_urun = st.selectbox("Ürün Seçin", df_kat['ad'].tolist())
        urun_bilgisi = df_kat[df_kat['ad'] == secilen_urun].iloc[0]
        
        st.write(f"Seçilen Ürün Birim Fiyatı: **{urun_bilgisi['fiyat']:,.2f} TL / {urun_bilgisi['birim']}**")
        miktar = st.number_input(f"Miktar ({urun_bilgisi['birim']})", min_value=1.0, value=1.0)
        
        toplam_tutar = miktar * urun_bilgisi['fiyat']
        st.write(f"Hesaplanan Tutar: **{toplam_tutar:,.2f} TL**")