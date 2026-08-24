import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import base64
from datetime import datetime, date
from io import BytesIO

st.set_page_config(page_title="ART DİZAYN ERP Panel", page_icon="🏗️", layout="wide")

# Yazdırma (PDF) Modunda Streamlit Arayüzünü Gizleme
st.markdown("""
<style>
@media print {
    [data-testid="stSidebar"], .stButton, header, footer, .stDownloadButton, [data-testid="stHeader"] {
        display: none !important;
    }
    .main .block-container {
        padding: 0 !important;
        margin: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Veritabanı Kurulumu
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

if 'teklif_kalemleri' not in st.session_state:
    st.session_state.teklif_kalemleri = []

def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        df_m = pd.read_sql_query("SELECT id as 'Müşteri No', firma_adi as 'Firma', yetkili as 'Yetkili', telefon as 'Telefon', adres as 'Adres' FROM musteriler", conn)
        df_m.to_excel(writer, sheet_name='Müşteriler', index=False)
        
        df_i = pd.read_sql_query("SELECT id as 'İş No', musteri_id as 'Müşteri No', isin_cinsi as 'İşin Cinsi', toplam_tutar as 'Tutar (TL)', tarih as 'Sözleşme Tarihi', montaj_tarihi as 'Montaj Tarihi' FROM isler", conn)
        df_i.to_excel(writer, sheet_name='İşler ve Montajlar', index=False)
        
        df_t = pd.read_sql_query("SELECT id as 'Tahsilat No', is_id as 'İş No', musteri_id as 'Müşteri No', odenen_tutar as 'Ödenen (TL)', tarih as 'Tarih', aciklama as 'Açıklama' FROM tahsilatlar", conn)
        df_t.to_excel(writer, sheet_name='Tahsilat Hareketleri', index=False)
        
        df_s = pd.read_sql_query("SELECT id as 'Stok No', malzeme_adi as 'Malzeme', kategori as 'Kategori', miktar as 'Miktar', birim as 'Birim', kritik_seviye as 'Kritik Seviye' FROM stok", conn)
        df_s.to_excel(writer, sheet_name='Depo Stok', index=False)
        
    return output.getvalue()

st.title("🏗️ ART DİZAYN - Bütünleşik İmalat & Finans ERP Paneli")

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

tab_grafik, tab_teklif, tab_musteri, tab_hesap, tab_proforma, tab_takvim, tab_stok = st.tabs([
    "📊 Finans & Grafikler", 
    "📄 Teklif Formu Oluştur",
    "👤 Müşteri & İş/Ödeme Kaydı", 
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

# ---------------------------------------------------------
# 2. TEKLİF FORMU OLUŞTURUCU (HTML KOD SIZINTISI GİDERİLDİ)
# ---------------------------------------------------------
with tab_teklif:
    st.subheader("📄 Kurumsal Teklif Formu Hazırlama Paneli")
    col_tf1, col_tf2 = st.columns([1, 1])
    
    with col_tf1:
        st.write("**1. Logo & Müşteri Bilgileri**")
        uploaded_logo = st.file_uploader("Firma Logosu Yükle (PNG / JPG)", type=["png", "jpg", "jpeg"])
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
            st.rerun()
            
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
        logo_html = f'<img src="{logo_base64}" style="max-height: 55px; margin-bottom: 5px;">' if logo_base64 else '<h1 style="color:#0F2C59; margin:0; font-family:sans-serif; font-weight:bold;">ART DİZAYN</h1>'
        
        table_rows_html = ""
        ara_toplam = 0.0
        for item in st.session_state.teklif_kalemleri:
            ara_toplam += item["Toplam Tutar"]
            table_rows_html += f"""<tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px;">
                <td style="padding: 8px; text-align: center;">{item['Sıra']}</td>
                <td style="padding: 8px;">{item['Açıklama']}</td>
                <td style="padding: 8px; text-align: center;">{item['Miktar']} {item['Birim']}</td>
                <td style="padding: 8px; text-align: right;">{item['Birim Fiyat']:,.2f} TL</td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">{item['Toplam Tutar']:,.2f} TL</td>
            </tr>"""
            
        kdv_tutar = ara_toplam * 0.20
        genel_toplam = ara_toplam + kdv_tutar
        formatted_sartlar = tf_sartlar.replace("\n", "<br>")
        
        teklif_html_full = f"""<div style="border: 1px solid #d1d5db; padding: 25px; border-radius: 8px; background-color: #ffffff; font-family: Arial, sans-serif; color: #1f2937;">
            <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #0F2C59; padding-bottom: 12px; margin-bottom: 15px;">
                <tr>
                    <td style="vertical-align: middle;">
                        {logo_html}
                        <p style="margin:2px 0 0 0; font-size: 10px; color: #4b5563; font-weight:600;">PVC, ALÜMİNYUM & CAM BALKON SİSTEMLERİ</p>
                    </td>
                    <td style="text-align: right; vertical-align: middle;">
                        <h3 style="margin:0; color: #0F2C59; letter-spacing: 1px;">FİYAT TEKLİF FORMU</h3>
                        <p style="margin:2px 0 0 0; font-size: 11px; color: #6b7280;"><b>Teklif No:</b> {tf_no}</p>
                        <p style="margin:0; font-size: 11px; color: #6b7280;"><b>Tarih:</b> {tf_tarih.strftime('%d.%m.%Y')}</p>
                    </td>
                </tr>
            </table>
            <div style="background-color: #f8fafc; border-left: 4px solid #0F2C59; padding: 10px 12px; margin-bottom: 15px; border-radius: 0 4px 4px 0;">
                <p style="margin:0; font-size: 12px;"><b>Sayın / Firma:</b> {tf_musteri}</p>
                <p style="margin:2px 0 0 0; font-size: 12px;"><b>İlgili Kişi:</b> {tf_yetkili} | <b>Tel:</b> {tf_tel}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                <thead>
                    <tr style="background-color: #0F2C59; color: #ffffff; font-size: 12px;">
                        <th style="padding: 8px; width: 5%; text-align: center;">#</th>
                        <th style="padding: 8px; text-align: left;">Ürün / Hizmet Açıklaması</th>
                        <th style="padding: 8px; text-align: center; width: 15%;">Miktar</th>
                        <th style="padding: 8px; text-align: right; width: 20%;">Birim Fiyat</th>
                        <th style="padding: 8px; text-align: right; width: 20%;">Toplam Tutar</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html if table_rows_html else '<tr><td colspan="5" style="padding:15px; text-align:center; color:#999; font-size:12px;">Henüz kalem eklenmedi.</td></tr>'}
                </tbody>
            </table>
            <table style="width: 250px; margin-left: auto; border-collapse: collapse; margin-top: 10px;">
                <tr>
                    <td style="padding: 4px 0; font-size: 12px; color: #475569;">Ara Toplam:</td>
                    <td style="padding: 4px 0; font-size: 12px; text-align: right; color: #475569;"><b>{ara_toplam:,.2f} TL</b></td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; font-size: 12px; color: #475569;">KDV (%20):</td>
                    <td style="padding: 4px 0; font-size: 12px; text-align: right; color: #475569;"><b>{kdv_tutar:,.2f} TL</b></td>
                </tr>
                <tr style="border-top: 2px solid #0F2C59;">
                    <td style="padding: 6px 0 0 0; font-size: 13px; font-weight: bold; color: #0F2C59;">GENEL TOPLAM:</td>
                    <td style="padding: 6px 0 0 0; font-size: 13px; font-weight: bold; text-align: right; color: #0F2C59;">{genel_toplam:,.2f} TL</td>
                </tr>
            </table>
            <div style="margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 10px;">
                <h5 style="margin:0 0 5px 0; color: #0F2C59; font-size:12px;">TEKLİF KOŞULLARI & ŞARTLAR</h5>
                <div style="font-size: 10px; color: #475569; line-height: 1.4; background-color: #fafafa; padding: 8px; border-radius: 4px;">
                    {formatted_sartlar}
                </div>
            </div>
            <table style="width: 100%; margin-top: 35px; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; text-align: center; font-size: 11px; color: #334155;">
                        <b>ART DİZAYN</b><br>Yetkili İmza / Kaşe
                        <div style="margin-top: 35px;">_______________________</div>
                    </td>
                    <td style="width: 50%; text-align: center; font-size: 11px; color: #334155;">
                        <b>MÜŞTERİ ONAYI</b><br>İmza / Tarih
                        <div style="margin-top: 35px;">_______________________</div>
                    </td>
                </tr>
            </table>
        </div>"""
        
        # HTML Render Komutu (unsafe_allow_html ZORUNLUDUR)
        st.markdown(teklif_html_full, unsafe_allow_html=True)
        st.info("💡 **PDF Çıktısı Almak İçin:** Klavyenizden **Ctrl + P** tuşlarına basarak *PDF Olarak Kaydet* seçebilirsiniz.")

# ---------------------------------------------------------
# 3. MÜŞTERİ YÖNETİMİ & BORÇ / İŞ / ÖDEME EKLEME
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Cari Yönetimi, Borç İşleme & Tahsilat")
    col_m1, col_m2 = st.columns([1, 2])
    
    with col_m1:
        st.write("### ➕ Yeni Müşteri Kaydı")
        f_adi = st.text_input("Firma / Müşteri Adı*")
        y_adi = st.text_input("Yetkili Adı")
        tel = st.text_input("Telefon", "+905320000000")
        adr = st.text_area("Adres")
        
        if st.button("💾 Müşteriyi Siste Kaydet", use_container_width=True):
            if f_adi.strip():
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)", (f_adi, y_adi, tel, adr))
                conn.commit()
                st.success("Müşteri kaydı yapıldı!")
                st.rerun()
            else:
                st.error("Lütfen müşteri adını girin!")

    with col_m2:
        st.write("### 🔍 Müşteri Listesi & Cari Durum")
        df_m = pd.read_sql_query("SELECT id as 'ID', firma_adi as 'Firma', yetkili as 'Yetkili', telefon as 'Telefon', adres as 'Adres' FROM musteriler", conn)
        
        if not df_m.empty:
            st.dataframe(df_m, use_container_width=True)
            st.markdown("---")
            st.write("### 🛠️ Müşteriye İş / Borç İşleme & Takvim Oluşturma")
            
            musteri_dict = dict(zip(df_m['ID'], df_m['Firma']))
            secilen_m_id = st.selectbox("İş / Borç Eklenecek Müşteriyi Seçin", options=list(musteri_dict.keys()), format_func=lambda x: f"{musteri_dict[x]} (ID: {x})")
            
            with st.form("is_ekle_form"):
                is_cinsi = st.text_input("İşin Cinsi / Açıklama", "Isıcamlı Cam Balkon Montajı")
                is_tutar = st.number_input("Toplam İş Bedeli / Borç Tutarı (TL)", value=10000.0, step=500.0)
                is_tarih = st.date_input("Sözleşme / İş Tarihi", value=date.today())
                montaj_tarihi = st.date_input("Montaj / Şantiye Tarihi (Takvime Düşer)", value=date.today())
                
                btn_is_ekle = st.form_submit_button("🛠️ İş Kaydını İşle ve Takvime Ekle")
                
                if btn_is_ekle:
                    c.execute("INSERT INTO isler (musteri_id, isin_cinsi, toplam_tutar, tarih, montaj_tarihi) VALUES (?, ?, ?, ?, ?)", 
                              (secilen_m_id, is_cinsi, is_tutar, is_tarih.strftime('%Y-%m-%d'), montaj_tarihi.strftime('%Y-%m-%d')))
                    conn.commit()
                    st.success(f"{musteri_dict[secilen_m_id]} müşterisine borç işlendi ve montaj takvime eklendi!")
                    st.rerun()
            
            st.markdown("---")
            st.write("### 💵 Ödeme (Tahsilat) Alma")
            df_m_isler = pd.read_sql_query(f"SELECT id, isin_cinsi, toplam_tutar FROM isler WHERE musteri_id = {secilen_m_id}", conn)
            
            if not df_m_isler.empty:
                is_dict = dict(zip(df_m_isler['id'], df_m_isler.apply(lambda r: f"{r['isin_cinsi']} - ({r['toplam_tutar']:,.2f} TL)", axis=1)))
                secilen_is_id = st.selectbox("Ödeme Alınacak İşi Seçin", options=list(is_dict.keys()), format_func=lambda x: is_dict[x])
                
                with st.form("tahsilat_form"):
                    odenen_tutar = st.number_input("Tahsil Edilen Tutar (TL)", value=1000.0, step=250.0)
                    tahsilat_tarihi = st.date_input("Tahsilat Tarihi", value=date.today())
                    aciklama = st.text_input("Açıklama / Ödeme Tipi", "EFT / Havale Parçalı Ödeme")
                    
                    btn_tahsilat = st.form_submit_button("💵 Ödemeyi Kaydet")
                    
                    if btn_tahsilat:
                        c.execute("INSERT INTO tahsilatlar (is_id, musteri_id, odenen_tutar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)", 
                                  (secilen_is_id, secilen_m_id, odenen_tutar, tahsilat_tarihi.strftime('%Y-%m-%d'), aciklama))
                        conn.commit()
                        st.success("Tahsilat kaydı başarıyla alındı!")
                        st.rerun()
            else:
                st.info("Bu müşteriye ait henüz tanımlanmış bir iş bulunmuyor.")
        else:
            st.warning("Kayıtlı müşteri bulunamadı.")

# ---------------------------------------------------------
# 4. ÖLÇÜ HESABI
# ---------------------------------------------------------
with tab_hesap:
    st.subheader("📏 En x Boy Ölçüsünden Otomatik Profil ve Cam Hesabı")
    c_h1, c_h2 = st.columns(2)
    en_cm = c_h1.number_input("En Ölçüsü (cm)", value=200.0, step=10.0)
    boy_cm = c_h2.number_input("Boy Ölçüsü (cm)", value=150.0, step=10.0)
    
    m2 = (en_cm / 100) * (boy_cm / 100)
    cevre_m = ((en_cm + boy_cm) * 2) / 100
    
    col_r1, col_r2 = st.columns(2)
    col_r1.metric("Net Cam / Kapatma Alanı", f"{m2:.2f} m²")
    col_r2.metric("Yaklaşık Kasa Profil Çevresi", f"{cevre_m:.2f} Metre")

# ---------------------------------------------------------
# 5. PROFORMA & WHATSAPP
# ---------------------------------------------------------
with tab_proforma:
    st.subheader("📑 PROFORMA FATURA VE WHATSAPP TEKLİFİ")
    p_mus = st.text_input("Müşteri / Firma Adı", "Ahmet Yılmaz")
    p_tel = st.text_input("WhatsApp Telefon (+90...)", "+905320000000")
    p_is = st.text_input("İş Detayı", "Isıcamlı Cam Balkon Kapatma")
    p_tutar = st.number_input("Toplam Bedel (TL)", value=38400.0)
    
    wa_mesaj = f"Sayın {p_mus},\nART DİZAYN Teklif Detayınız:\nİş: {p_is}\nTutar: {p_tutar:,.2f} TL"
    wa_link = f"https://wa.me/{p_tel.replace('+','').replace(' ','')}?text={urllib.parse.quote(wa_mesaj)}"
    
    st.markdown(f"[📲 WHATSAPP İLE TEKLİF GÖNDER]({wa_link})")

# ---------------------------------------------------------
# 6. ŞANTİYE & MONTAJ TAKVİMİ
# ---------------------------------------------------------
with tab_takvim:
    st.subheader("🗓️ Şantiye Montaj Takvimi & Planlama")
    
    df_takvim = pd.read_sql_query("""
        SELECT 
            isler.montaj_tarihi as 'Montaj Tarihi',
            musteriler.firma_adi as 'Müşteri / Firma',
            musteriler.yetkili as 'Yetkili',
            musteriler.telefon as 'Telefon',
            isler.isin_cinsi as 'İş Açıklaması',
            isler.toplam_tutar as 'Tutar (TL)'
        FROM isler
        JOIN musteriler ON isler.musteri_id = musteriler.id
        ORDER BY isler.montaj_tarihi ASC
    """, conn)
    
    if not df_takvim.empty:
        st.dataframe(df_takvim, use_container_width=True)
    else:
        st.info("Planlanmış bir şantiye montajı bulunmuyor.")

# ---------------------------------------------------------
# 7. DEPO & STOK TAKİBİ
# ---------------------------------------------------------
with tab_stok:
    st.subheader("📦 Depo & Stok Takibi")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.write("### ➕ Stok / Malzeme Ekle")
        stk_adi = st.text_input("Malzeme Adı", "8mm Füme Cam")
        stk_kat = st.selectbox("Kategori", ["Cam", "Alüminyum Profil", "PVC Profil", "Aksesuar", "Fitil/Sızdırmazlık"])
        stk_mikt = st.number_input("Miktar", value=100.0)
        stk_brm = st.selectbox("Birim", ["m²", "Boy (6m)", "Adet", "Kg", "Metre"])
        stk_krt = st.number_input("Kritik Stok Seviyesi", value=20.0)
        
        if st.button("💾 Malzemeyi Depoya Ekle", use_container_width=True):
            if stk_adi:
                c.execute("INSERT INTO stok (malzeme_adi, kategori, miktar, birim, kritik_seviye) VALUES (?, ?, ?, ?, ?)",
                          (stk_adi, stk_kat, stk_mikt, stk_brm, stk_krt))
                conn.commit()
                st.success("Stok eklendi!")
                st.rerun()
                
    with col_s2:
        st.write("### 📋 Depo Durumu")
        df_stok_data = pd.read_sql_query("SELECT id as 'ID', malzeme_adi as 'Malzeme', kategori as 'Kategori', miktar as 'Miktar', birim as 'Birim', kritik_seviye as 'Kritik Seviye' FROM stok", conn)
        st.dataframe(df_stok_data, use_container_width=True)
