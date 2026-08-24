import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Sayfa Yapılandırması
st.set_page_config(page_title="ART DİZAYN Panel", page_icon="🏗️", layout="wide")

# SQLite Veritabanı ve Tablo Oluşturma
conn = sqlite3.connect('art_dizayn_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS musteriler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_adi TEXT, yetkili TEXT, telefon TEXT, adres TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS isler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, musteri_id INTEGER, isin_cinsi TEXT, toplam_tutar REAL, tarih TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tahsilatlar 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_id INTEGER, musteri_id INTEGER, odenen_tutar REAL, tarih TEXT, aciklama TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS malzemeler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, ad TEXT, birim TEXT, fiyat REAL)''')
conn.commit()

# --- BAŞLIK ---
st.title("🏗️ ART DİZAYN - Kurumsal Yönetim Paneli")

# --- SEKMELER ---
tab_grafik, tab_musteri, tab_proforma, tab_arama, tab_malzeme = st.tabs([
    "📊 Görsel Grafikler & Özet", 
    "👤 Müşteri Cari Hesapları", 
    "📑 ART DİZAYN Proforma Fatura", 
    "🔍 Müşteri & Borç Arama", 
    "📦 Malzeme Kataloğu"
])

# ---------------------------------------------------------
# 1. GÖRSEL GRAFİKLER VE ÖZET DÖKÜM
# ---------------------------------------------------------
with tab_grafik:
    st.subheader("📈 Finansal Durum & Analiz Grafikleri")
    
    # Genel Hesaplamalar
    df_isler = pd.read_sql_query("SELECT * FROM isler", conn)
    df_tahsilat = pd.read_sql_query("SELECT * FROM tahsilatlar", conn)
    
    toplam_is_hacmi = df_isler['toplam_tutar'].sum() if not df_isler.empty else 0.0
    toplam_tahsilat = df_tahsilat['odenen_tutar'].sum() if not df_tahsilat.empty else 0.0
    kalan_alacak = toplam_is_hacmi - toplam_tahsilat
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İş Hacmi", f"{toplam_is_hacmi:,.2f} TL")
    col2.metric("Tahsil Edilen (Kasa)", f"{toplam_tahsilat:,.2f} TL")
    col3.metric("Kalan Net Alacak", f"{kalan_alacak:,.2f} TL", delta=f"-{kalan_alacak:,.2f} TL", delta_color="inverse")
    
    st.markdown("---")
    
    # Grafik Gösterimi
    if toplam_is_hacmi > 0:
        grafik_data = pd.DataFrame({
            "Durum": ["Tahsil Edilen (Kasa)", "Kalan Alacak"],
            "Tutar (TL)": [toplam_tahsilat, kalan_alacak]
        })
        st.write("**Alacak / Tahsilat Oranı Grafik Gösterimi**")
        st.bar_chart(data=grafik_data.set_index("Durum"), use_container_width=True)
    else:
        st.info("Henüz grafik oluşturacak iş kaydı bulunmamaktadır.")

# ---------------------------------------------------------
# 2. MÜŞTERİ CARİ HESAPLARI & İŞ / TAHSİLAT EKLEME
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Kaydı ve İş/Ödeme Takibi")
    
    col_m1, col_m2 = st.columns([1, 2])
    
    with col_m1:
        st.write("**Yeni Müşteri Ekle**")
        f_adi = st.text_input("Firma / Müşteri Adı")
        y_adi = st.text_input("Yetkili Kişi")
        tel = st.text_input("Telefon")
        adres = st.text_area("Adres")
        
        if st.button("💾 Müşteriyi Kaydet", use_container_width=True):
            if f_adi:
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)",
                          (f_adi, y_adi, tel, adres))
                conn.commit()
                st.success(f"{f_adi} veritabanına eklendi.")
                st.rerun()
            else:
                st.warning("Lütfen firma adını giriniz.")

    with col_m2:
        df_mus = pd.read_sql_query("SELECT id, firma_adi FROM musteriler", conn)
        
        if not df_mus.empty:
            st.write("**Müşteriye İş veya Ödeme (Tahsilat) Ekle**")
            secilen_mus_id = st.selectbox("Müşteri Seçin", df_mus['id'].tolist(), format_func=lambda x: df_mus[df_mus['id']==x]['firma_adi'].values[0])
            
            islem_turu = st.radio("İşlem Türü", ["🛠️ Yeni İş/Proje Tanımla", "💵 Ödeme Al (Borçtan Düş)"], horizontal=True)
            
            if islem_turu == "🛠️ Yeni İş/Proje Tanımla":
                is_cinsi = st.text_input("Yapılan İşin Cinsi (Örn: Cam Balkon & Alüminyum Küpeşte)")
                is_tutar = st.number_input("İş Bedeli (TL)", min_value=0.0, step=1000.0)
                if st.button("💾 İşi Müşteriye İşle"):
                    c.execute("INSERT INTO isler (musteri_id, isin_cinsi, toplam_tutar, tarih) VALUES (?, ?, ?, ?)",
                              (secilen_mus_id, is_cinsi, is_tutar, str(datetime.now().strftime("%Y-%m-%d"))))
                    conn.commit()
                    st.success("İş kaydı eklendi!")
                    st.rerun()
                    
            else:  # Tahsilat Ekleme
                df_musteri_isleri = pd.read_sql_query(f"SELECT id, isin_cinsi, toplam_tutar FROM isler WHERE musteri_id={secilen_mus_id}", conn)
                if not df_musteri_isleri.empty:
                    secilen_is_id = st.selectbox("İlgili İşi Seçin", df_musteri_isleri['id'].tolist(), format_func=lambda x: f"{df_musteri_isleri[df_musteri_isleri['id']==x]['isin_cinsi'].values[0]} ({df_musteri_isleri[df_musteri_isleri['id']==x]['toplam_tutar'].values[0]:,.2f} TL)")
                    odenen = st.number_input("Alınan Ödeme Tutarı (TL)", min_value=0.0, step=500.0)
                    aciklama = st.text_input("Ödeme Açıklaması (Örn: Banka Havalesi / Nakit Kapora)")
                    if st.button("💵 Ödemeyi Düş"):
                        c.execute("INSERT INTO tahsilatlar (is_id, musteri_id, odenen_tutar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)",
                                  (secilen_is_id, secilen_mus_id, odenen, str(datetime.now().strftime("%Y-%m-%d")), aciklama))
                        conn.commit()
                        st.success("Ödeme alındı ve borçtan düşüldü!")
                        st.rerun()
                else:
                    st.info("Bu müşteriye ait kayıtlı iş bulunamadı.")

# ---------------------------------------------------------
# 3. ART DİZAYN PROFORMA FATURA OLUŞTURUCU
# ---------------------------------------------------------
with tab_proforma:
    st.subheader("📑 ART DİZAYN Proforma Fatura Hazırlayıcı")
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        p_musteri = st.text_input("Müşteri / Firma Unvanı", "Örnek Müşteri A.Ş.")
        p_tel = st.text_input("Müşteri Telefon", "+90 532 XXX XX XX")
        p_no = st.text_input("Proforma No", f"PRF-{datetime.now().strftime('%Y%m%d')}")
    with c_p2:
        p_tarih = st.date_input("Fatura Tarihi")
        p_adres = st.text_area("Müşteri Adresi", "Denizli / Türkiye")

    st.markdown("---")
    st.write("**Fatura Kalemleri**")
    
    df_p_init = pd.DataFrame([
        {"İş / Malzeme Açıklaması": "PVC Pencere Doğrama Sistemi", "Miktar": 20.0, "Birim": "m²", "Birim Fiyat (TL)": 2500.0},
        {"İş / Malzeme Açıklaması": "Isıcamlı Cam Balkon Kapatma", "Miktar": 10.0, "Birim": "m²", "Birim Fiyat (TL)": 3500.0}
    ])
    
    edited_p_df = st.data_editor(df_p_init, num_rows="dynamic", use_container_width=True)
    
    edited_p_df["Toplam"] = edited_p_df["Miktar"] * edited_p_df["Birim Fiyat (TL)"]
    ara_toplam = edited_p_df["Toplam"].sum()
    kdv = ara_toplam * 0.20
    genel_toplam = ara_toplam + kdv
    
    st.markdown("---")
    # CANLI PROFORMA ÖN İZLEMESİ
    st.markdown(f"""
    ```text
    ========================================================================================
    ART DİZAYN                                                    PROFORMA FATURA
    PVC Doğrama, Alüminyum & Cam Balkon Sistemleri                 Tarih   : {p_tarih}
                                                                  Belge No: {p_no}
    ----------------------------------------------------------------------------------------
    SAYIN (MÜŞTERİ):                              FİRMA / YÜKLENİCİ:
    {p_musteri}                                   ART DİZAYN SİSTEMLERİ
    Tel  : {p_tel}                                Tel  : +90 (5XX) XXX XX XX
    Adres: {p_adres}                              E-posta: info@artdizayn.com
    ----------------------------------------------------------------------------------------
    ARA TOPLAM  : {ara_toplam:,.2f} TL
    KDV (%20)   : {kdv:,.2f} TL
    GENEL TOPLAM: {genel_toplam:,.2f} TL
    ========================================================================================
    ```
    """)

# ---------------------------------------------------------
# 4. MÜŞTERİ & BORÇ ARAMA (DETAYLI CARİ KART)
# ---------------------------------------------------------
with tab_arama:
    st.subheader("🔍 Arama: Müşteri Borç / Alacak Detayları")
    
    arama_metni = st.text_input("Arama Yapın (Firma veya Müşteri Adı Giriniz):")
    
    if arama_metni:
        query = f"SELECT * FROM musteriler WHERE firma_adi LIKE '%{arama_metni}%' OR yetkili LIKE '%{arama_metni}%'"
        df_sonuc = pd.read_sql_query(query, conn)
        
        if not df_sonuc.empty:
            for index, row in df_sonuc.iterrows():
                m_id = row['id']
                st.markdown(f"### 🏢 {row['firma_adi']} (Yetkili: {row['yetkili']})")
                st.write(f"**Telefon:** {row['telefon']} | **Adres:** {row['adres']}")
                
                # Müşterinin İşleri
                df_m_isler = pd.read_sql_query(f"SELECT id, isin_cinsi, toplam_tutar, tarih FROM isler WHERE musteri_id={m_id}", conn)
                
                if not df_m_isler.empty:
                    toplam_borcu = df_m_isler['toplam_tutar'].sum()
                    
                    # Yapılan Ödemeler
                    df_m_ode = pd.read_sql_query(f"SELECT odenen_tutar FROM tahsilatlar WHERE musteri_id={m_id}", conn)
                    toplam_odenen = df_m_ode['odenen_tutar'].sum() if not df_m_ode.empty else 0.0
                    
                    kalan_bakiye = toplam_borcu - toplam_odenen
                    
                    ca1, ca2, ca3 = st.columns(3)
                    ca1.metric("Toplam Yapılan İş Bedeli", f"{toplam_borcu:,.2f} TL")
                    ca2.metric("Toplam Alınan Ödeme", f"{toplam_odenen:,.2f} TL")
                    ca3.metric("KALAN BORÇ (BAKİYE)", f"{kalan_bakiye:,.2f} TL", delta=f"{kalan_bakiye:,.2f} TL", delta_color="inverse")
                    
                    st.write("**Yapılan İşlerin Detayı:**")
                    st.dataframe(df_m_isler, use_container_width=True)
                else:
                    st.info("Bu müşteriye ait kayıtlı iş bulunamadı.")
                st.markdown("---")
        else:
            st.warning("Eşleşen müşteri bulunamadı.")

# ---------------------------------------------------------
# 5. MALZEME KATALOĞU
# ---------------------------------------------------------
with tab_malzeme:
    st.subheader("📦 Malzeme & Birim Fiyat Kataloğu")
    df_malz = pd.read_sql_query("SELECT * FROM malzemeler", conn)
    st.dataframe(df_malz, use_container_width=True)
