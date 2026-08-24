import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import base64
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="ART DİZAYN ERP Panel", page_icon="🏗️", layout="wide")

# Veritabanı Mimarisi
conn = sqlite3.connect('art_dizayn_full.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS musteriler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_adi TEXT, yetkili TEXT, telefon TEXT, adres TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS isler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, musteri_id INTEGER, isin_cinsi TEXT, toplam_tutar REAL, tarih TEXT, montaj_tarihi TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tahsilatlar 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_id INTEGER, musteri_id INTEGER, odenen_tutar REAL, tarih TEXT, aciklama TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS stok 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, malzeme_adi TEXT, kategori TEXT, miktar REAL, birim TEXT, kritik_seviye REAL)''')
conn.commit()

# Session State Hazırlığı
if 'teklif_kalemleri' not in st.session_state:
    st.session_state.teklif_kalemleri = []

# --- EXCEL RAPOR ÜRETİCİ FONKSİYON ---
def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_m = pd.read_sql_query("SELECT id as 'Müşteri No', firma_adi as 'Firma', yetkili as 'Yetkili', telefon as 'Telefon', adres as 'Adres' FROM musteriler", conn)
        df_m.to_excel(writer, sheet_name='Müşteriler', index=False)
        
        df_i = pd.read_sql_query("SELECT id as 'İş No', musteri_id as 'Müşteri No', isin_cinsi as 'İşin Cinsi', toplam_tutar as 'Tutar (TL)', tarih as 'Sözleşme Tarihi', montaj_tarihi as 'Montaj Tarihi' FROM isler", conn)
        df_i.to_excel(writer, sheet_name='İşler ve Montajlar', index=False)
        
        df_t = pd.read_sql_query("SELECT id as 'Tahsilat No', is_id as 'İş No', musteri_id as 'Müşteri No', odenen_tutar as 'Ödenen (TL)', tarih as 'Tarih', aciklama as 'Açıklama' FROM tahsilatlar", conn)
        df_t.to_excel(writer, sheet_name='Tahsilat Hareketleri', index=False)
        
        df_s = pd.read_sql_query("SELECT id as 'Stok No', malzeme_adi as 'Malzeme', kategori as 'Kategori', miktar as 'Miktar', birim as 'Birim', kritik_seviye as 'Kritik Seviye' FROM stok", conn)
        df_s.to_excel(writer, sheet_name='Depo Stok', index=False)
        
    processed_data = output.getvalue()
    return processed_data

st.title("🏗️ ART DİZAYN - Bütünleşik İmalat & Finans ERP Paneli")

# --- ÜST YÖNETİM ALANI ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.caption("ART DİZAYN PVC, Alüminyum & Cam Balkon Sistemleri Yönetim Ekranı")
with col_head2:
    excel_data = to_excel()
    st.download_button(
        label="📊 Tüm Verileri Excel Olarak İndir",
        data=excel_data,
        file_name=f"ART_DIZAYN_Sistem_Raporu_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.markdown("---")

# GELİŞMİŞ SEKMELER
tab_grafik, tab_teklif, tab_musteri, tab_hesap, tab_proforma, tab_takvim, tab_stok = st.tabs([
    "📊 Finans & Grafikler", 
    "📄 Teklif Formu Oluştur",
    "👤 Müşteri & Borç Arama", 
    "📏 Ölçü & Metraj Hesabı",
    "📑 Proforma & WhatsApp", 
    "🗓️ Şantiye Montaj Takvimi",
    "📦 Depo & Stok Takibi"
])

# ---------------------------------------------------------
# 1. FİNANS VE GRAFİKLER
# ---------------------------------------------------------
with tab_grafik:
    st.subheader("📈 Genel Finansal Özet")
    df_isler = pd.read_sql_query("SELECT * FROM isler", conn)
    df_tahsilat = pd.read_sql_query("SELECT * FROM tahsilatlar", conn)
    
    toplam_is = df_isler['toplam_tutar'].sum() if not df_isler.empty else 0.0
    toplam_tahsilat = df_tahsilat['odenen_tutar'].sum() if not df_tahsilat.empty else 0.0
    kalan_alacak = toplam_is - toplam_tahsilat
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İş Hacmi", f"{toplam_is:,.2f} TL")
    col2.metric("Tahsil Edilen (Kasa)", f"{toplam_tahsilat:,.2f} TL")
    col3.metric("Kalan Net Alacak", f"{kalan_alacak:,.2f} TL")
    
    if toplam_is > 0:
        st.markdown("---")
        st.write("**Tahsilat / Alacak Dağılımı Grafik Gösterimi**")
        grafik_df = pd.DataFrame({
            "Durum": ["Kasadaki (Tahsilat)", "Saha Alacağı"],
            "Tutar (TL)": [toplam_tahsilat, kalan_alacak]
        })
        st.bar_chart(grafik_df.set_index("Durum"), use_container_width=True)

# ---------------------------------------------------------
# 2. TEKLİF FORMU OLUŞTURUCU (Geliştirilmiş & Görsel Tasarım)
# ---------------------------------------------------------
with tab_teklif:
    st.subheader("📄 Kurumsal Teklif Formu Hazırlama Paneli")
    
    col_tf1, col_tf2 = st.columns([1, 1])
    
    with col_tf1:
        st.write("**1. Firma Logosu & Müşteri Bilgileri**")
        uploaded_logo = st.file_drop_target if hasattr(st, "file_drop_target") else st.file_uploader("Firma Logosu Yükle (PNG / JPG)", type=["png", "jpg", "jpeg"])
        
        logo_base64 = ""
        if uploaded_logo is not None:
            bytes_data = uploaded_logo.getvalue()
            logo_base64 = f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
            
        tf_musteri = st.text_input("Müşteri / Firma Adı", "Örnek İnşaat Ltd. Şti.")
        tf_yetkili = st.text_input("Yetkili Kişi", "Ahmet Yılmaz")
        tf_tel = st.text_input("Müşteri Telefon", "+90 532 000 00 00")
        tf_no = st.text_input("Teklif No", f"ART-{datetime.now().strftime('%Y%m%d')}-01")
        tf_tarih = st.date_input("Teklif Tarihi")
        
        st.markdown("---")
        st.write("**2. Ürün / Kalem Ekleme**")
        kalem_aciklama = st.text_input("Ürün / Hizmet Detayı", "8mm Füme Camlı Isıcamlı Balkon Kapatma Sistemi")
        c_k1, c_k2, c_k3 = st.columns(3)
        kalem_miktar = c_k1.number_input("Miktar / Ölçü", value=15.0, step=1.0)
        kalem_birim = c_k2.selectbox("Birim", ["m²", "Metre", "Adet", "Set", "Takım"])
        kalem_fiyat = c_k3.number_input("Birim Fiyat (TL)", value=3500.0, step=100.0)
        
        if st.button("➕ Kalemi Teklife Ekle", use_container_width=True):
            toplam = kalem_miktar * kalem_fiyat
            st.session_state.teklif_kalemleri.append({
                "Sıra": len(st.session_state.teklif_kalemleri) + 1,
                "Açıklama": kalem_aciklama,
                "Miktar": kalem_miktar,
                "Birim": kalem_birim,
                "Birim Fiyat": kalem_fiyat,
                "Toplam Tutar": toplam
            })
            st.success("Kalem eklendi.")
            
        if st.button("🗑️ Kalemleri Temizle"):
            st.session_state.teklif_kalemleri = []
            st.rerun()

        st.markdown("---")
        st.write("**3. Özel Teklif Şartları & Notlar**")
        tf_sartlar = st.text_area("Teklif Şartları Metni", 
"""1. Bu teklif verildiği tarihten itibaren 15 gün süreyle geçerlidir.
2. Ödeme koşulları: %50 Siparişte, %50 Montaj tesliminde tahsil edilir.
3. Teslimat süresi ölçü alımından itibaren 10 iş günüdür.
4. Ürünlerimiz 2 yıl sızdırmazlık ve mekanizma garantisi altındadır.""", height=130)

    with col_tf2:
        st.write("**4. Resmi Teklif Formu Önizlemesi**")
        
        # Logo Gösterimi Mantığı
        logo_html = f'<img src="{logo_base64}" style="max-height: 60px; margin-bottom: 5px;">' if logo_base64 else '<h1 style="color:#0F2C59; margin:0; font-family:sans-serif; font-weight:bold;">ART DİZAYN</h1>'
        
        # Şık Teklif Formu Tasarımı (HTML & CSS)
        st.markdown(f"""
        <div style="border: 1px solid #d1d5db; padding: 25px; border-radius: 10px; background-color: #ffffff; font-family: 'Helvetica Neue', Arial, sans-serif; color: #1f2937; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            
            <!-- HEADER -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #0F2C59; padding-bottom: 15px; margin-bottom: 20px;">
                <div>
                    {logo_html}
                    <p style="margin:0; font-size: 11px; color: #4b5563; font-weight:600;">PVC, ALÜMİNYUM & CAM BALKON SİSTEMLERİ</p>
                </div>
                <div style="text-align: right;">
                    <h3 style="margin:0; color: #0F2C59; letter-spacing: 1px;">FİYAT TEKLİF FORMU</h3>
                    <p style="margin:3px 0 0 0; font-size: 12px; color: #6b7280;"><b>Teklif No:</b> {tf_no}</p>
                    <p style="margin:0; font-size: 12px; color: #6b7280;"><b>Tarih:</b> {tf_tarih.strftime('%d.%m.%Y')}</p>
                </div>
            </div>
            
            <!-- MÜŞTERİ BİLGİLERİ -->
            <div style="background-color: #f8fafc; border-left: 4px solid #0F2C59; padding: 12px 15px; margin-bottom: 20px; border-radius: 0 6px 6px 0;">
                <p style="margin:0; font-size: 13px;"><b>Sayın / Firma:</b> {tf_musteri}</p>
                <p style="margin:3px 0 0 0; font-size: 13px;"><b>İlgili Kişi:</b> {tf_yetkili} | <b>Tel:</b> {tf_tel}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # TABLO VE TOPLAM ALANI
        if st.session_state.teklif_kalemleri:
            df_tk = pd.DataFrame(st.session_state.teklif_kalemleri)
            st.dataframe(df_tk.drop(columns=["Sıra"]), use_container_width=True)
            
            ara_toplam = df_tk["Toplam Tutar"].sum()
            kdv_tutar = ara_toplam * 0.20
            genel_toplam = ara_toplam + kdv_tutar
            
            formatted_sartlar = tf_sartlar.replace("\n", "<br>")
            
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-top: 15px;">
                <div style="width: 260px; background-color: #f1f5f9; padding: 12px; border-radius: 6px; text-align: right; font-size: 13px;">
                    <p style="margin: 3px 0; color: #475569;">Ara Toplam: <b>{ara_toplam:,.2f} TL</b></p>
                    <p style="margin: 3px 0; color: #475569;">KDV (%20): <b>{kdv_tutar:,.2f} TL</b></p>
                    <div style="border-top: 2px solid #0F2C59; margin-top: 6px; padding-top: 6px;">
                        <span style="font-size: 15px; font-weight: bold; color: #0F2C59;">GENEL TOPLAM:<br>{genel_toplam:,.2f} TL</span>
                    </div>
                </div>
            </div>
            
            <!-- ŞARTLAR VE İMZA -->
            <div style="margin-top: 25px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                <h5 style="margin:0 0 8px 0; color: #0F2C59;">TEKLİF KOŞULLARI & ŞARTLAR</h5>
                <div style="font-size: 11px; color: #475569; line-height: 1.5; background-color: #fafafa; padding: 10px; border-radius: 5px;">
                    {formatted_sartlar}
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; margin-top: 35px; text-align: center; font-size: 12px; color: #334155;">
                <div style="width: 40%;">
                    <p style="margin-bottom: 40px;"><b>ART DİZAYN</b><br>Yetkili İmza / Kaşe</p>
                    <p>_______________________</p>
                </div>
                <div style="width: 40%;">
                    <p style="margin-bottom: 40px;"><b>MÜŞTERİ ONAYI</b><br>İmza / Tarih</p>
                    <p>_______________________</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
            
            st.info("💡 **İpucu:** Formu PDF olarak kaydetmek için klavyenizden **Ctrl + P** (Mac kullanıyorsanız **Cmd + P**) tuşlarına basıp hedefleri *PDF Olarak Kaydet* seçebilirsiniz.")
        else:
            st.markdown("</div>", unsafe_allow_html=True)
            st.warning("Teklif formunda görünecek ürün/hizmet kalemlerini sol menüden ekleyebilirsiniz.")

# ---------------------------------------------------------
# 3. MÜŞTERİ CARİ & ARAMA
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Cari Yönetimi ve Arama")
    
    c_m1, c_m2 = st.columns([1, 2])
    with c_m1:
        st.write("**Yeni Müşteri Kaydı**")
        f_adi = st.text_input("Firma / Müşteri Adı")
        y_adi = st.text_input("Yetkili Adı")
        tel = st.text_input("Telefon (Başında +90 ile)", "+905321112233")
        adr = st.text_area("Adres")
        if st.button("💾 Müşteriyi Kaydet", use_container_width=True):
            if f_adi:
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)",
                          (f_adi, y_adi, tel, adr))
                conn.commit()
                st.success("Müşteri veritabanına eklendi.")
                st.rerun()

    with c_m2:
        arama = st.text_input("🔍 Müşteri / Firma Adı İle Arama Yapın:")
        if arama:
            res = pd.read_sql_query(f"SELECT * FROM musteriler WHERE firma_adi LIKE '%{arama}%' OR yetkili LIKE '%{arama}%'", conn)
            for idx, r in res.iterrows():
                m_id = r['id']
                st.markdown(f"### 🏢 {r['firma_adi']} | Yetkili: {r['yetkili']}")
                st.write(f"📞 **Tel:** {r['telefon']} | 📍 **Adres:** {r['adres']}")
                
                is_df = pd.read_sql_query(f"SELECT * FROM isler WHERE musteri_id={m_id}", conn)
                if not is_df.empty:
                    top_borc = is_df['toplam_tutar'].sum()
                    ode_df = pd.read_sql_query(f"SELECT sum(odenen_tutar) as ode FROM tahsilatlar WHERE musteri_id={m_id}", conn)
                    top_ode = ode_df['ode'].iloc[0] if ode_df['ode'].iloc[0] is not None else 0.0
                    net_kal = top_borc - top_ode
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Toplam İş Bedeli", f"{top_borc:,.2f} TL")
                    m2.metric("Ödenen Tutar", f"{top_ode:,.2f} TL")
                    m3.metric("KALAN BAKİYE", f"{net_kal:,.2f} TL")
                    
                    st.dataframe(is_df[['isin_cinsi', 'toplam_tutar', 'tarih', 'montaj_tarihi']], use_container_width=True)
                else:
                    st.info("Kayıtlı iş bulunamadı.")
                st.markdown("---")

# ---------------------------------------------------------
# 4. ÖLÇÜ & METRAJ OTOMATİK HESAPLAYICI
# ---------------------------------------------------------
with tab_hesap:
    st.subheader("📏 En x Boy Ölçüsünden Otomatik Profil ve Cam Hesabı")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        en_cm = st.number_input("En Ölçüsü (cm)", value=200.0, step=10.0)
        boy_cm = st.number_input("Boy Ölçüsü (cm)", value=150.0, step=10.0)
        cam_birim_fiyat = st.number_input("Cam m² Fiyatı (TL)", value=3200.0, step=100.0)
        profil_birim_fiyat = st.number_input("Profil Metre Fiyatı (TL)", value=450.0, step=50.0)
    
    with col_h2:
        en_m = en_cm / 100.0
        boy_m = boy_cm / 100.0
        
        cam_alani = en_m * boy_m
        cam_fireli = cam_alani * 1.10
        profil_cevre = (en_m + boy_m) * 2
        
        toplam_cam_maliyeti = cam_fireli * cam_birim_fiyat
        toplam_profil_maliyeti = profil_cevre * profil_birim_fiyat
        genel_imalat_maliyeti = toplam_cam_maliyeti + toplam_profil_maliyeti
        
        st.success(f"📐 **Net Cam Alanı:** {cam_alani:.2f} m² (Fireli: {cam_fireli:.2f} m²)")
        st.success(f"📏 **Gerekli Profil:** {profil_cevre:.2f} Metre")
        st.write(f"**Tahmini Hesaplanan İmalat Bedeli:** {genel_imalat_maliyeti:,.2f} TL")

# ---------------------------------------------------------
# 5. PROFORMA FATURA VE WHATSAPP
# ---------------------------------------------------------
with tab_proforma:
    st.subheader("📑 PROFORMA FATURA VE WHATSAPP TEKLİFİ")
    
    p_mus = st.text_input("Müşteri Adı", "Ahmet Yılmaz")
    p_tel = st.text_input("WhatsApp Telefon (+90...)", "+905320000000")
    p_is = st.text_input("İş Açıklaması", "12 m² Isıcamlı Cam Balkon Kapatma")
    p_tutar = st.number_input("Toplam İş Bedeli (TL)", value=38400.0, step=1000.0)
    
    kdv = p_tutar * 0.20
    g_toplam = p_tutar + kdv
    
    wa_mesaj = f"Sayın {p_mus},\nART DİZAYN teklif detayınız aşağıdadır:\n\nİş: {p_is}\nTutar: {p_tutar:,.2f} TL\nKDV (%20): {kdv:,.2f} TL\n*GENEL TOPLAM: {g_toplam:,.2f} TL*\n\nTeklifimiz 15 gün geçerlidir."
    wa_link = f"https://wa.me/{p_tel.replace('+','').replace(' ','')}?text={urllib.parse.quote(wa_mesaj)}"
    
    st.markdown(f"[📲 WHATSAPP İLE TEKLİF GÖNDER]({wa_link})")

# ---------------------------------------------------------
# 6. ŞANTİYE MONTAJ TAKVİMİ
# ---------------------------------------------------------
with tab_takvim:
    st.subheader("🗓️ Şantiye & Montaj Planlayıcısı")
    
    df_m_list = pd.read_sql_query("SELECT id, firma_adi FROM musteriler", conn)
    if not df_m_list.empty:
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            sec_m = st.selectbox("Montaj Yapılacak Müşteri", df_m_list['id'].tolist(), format_func=lambda x: df_m_list[df_m_list['id']==x]['firma_adi'].values[0])
            m_is_cinsi = st.text_input("Montaj İş Cinsi", "PVC Pencere ve Cam Balkon Montajı")
            m_tutar = st.number_input("İş Tutar (TL)", value=25000.0)
            m_tarih = st.date_input("Montaj Tarihi")
            
            if st.button("📅 Montajı Takvime Ekle", use_container_width=True):
                c.execute("INSERT INTO isler (musteri_id, isin_cinsi, toplam_tutar, tarih, montaj_tarihi) VALUES (?, ?, ?, ?, ?)",
                          (sec_m, m_is_cinsi, m_tutar, str(datetime.now().strftime("%Y-%m-%d")), str(m_tarih)))
                conn.commit()
                st.success("Montaj takvime eklendi.")
                st.rerun()

        with c_t2:
            st.write("**Gelecek Montaj Programı**")
            df_plan = pd.read_sql_query("SELECT isin_cinsi, toplam_tutar, montaj_tarihi FROM isler WHERE montaj_tarihi IS NOT NULL ORDER BY montaj_tarihi ASC", conn)
            st.dataframe(df_plan, use_container_width=True)

# ---------------------------------------------------------
# 7. DEPO VE STOK TAKİBİ
# ---------------------------------------------------------
with tab_stok:
    st.subheader("📦 Tedarikçi Depo & Stok Yönetimi")
    
    cs1, cs2 = st.columns([1, 2])
    with cs1:
        st.write("**Yeni Stok Girişi**")
        s_ad = st.text_input("Malzeme Adı (Örn: Alüminyum Küpeşte Profili)")
        s_kat = st.selectbox("Kategori", ["Alüminyum Profil", "PVC Profil", "Cam", "Aksesuar/Kilit"])
        s_mikt = st.number_input("Mevcut Stok Miktarı", min_value=0.0, value=100.0)
        s_birim = st.selectbox("Birim", ["Metre", "Boy", "m²", "Adet", "Kutu"])
        s_kritik = st.number_input("Kritik Stok Uyarısı", value=20.0)
        
        if st.button("💾 Stok Ekle", use_container_width=True):
            c.execute("INSERT INTO stok (malzeme_adi, kategori, miktar, birim, kritik_seviye) VALUES (?, ?, ?, ?, ?)",
                      (s_ad, s_kat, s_mikt, s_birim, s_kritik))
            conn.commit()
            st.success("Stok eklendi.")
            st.rerun()

    with cs2:
        st.write("**Mevcut Depo Durumu**")
        df_stok = pd.read_sql_query("SELECT * FROM stok", conn)
        st.dataframe(df_stok, use_container_width=True)
