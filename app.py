import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import base64
from datetime import datetime, date
from io import BytesIO

st.set_page_config(page_title="ART DİZAYN ERP Panel", page_icon="🏗️", layout="wide")

# Mobil Uyum ve A4 Otomatik Baskı Formatı (CSS)
st.markdown("""
<style>
/* Mobil Ekran İyileştirmeleri */
@media (max-width: 768px) {
    .stButton button { width: 100% !important; margin-bottom: 5px; }
    [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
}

/* A4 Sayfaya Otomatik Sığdırma ve Yazdırma Düzeni */
@media print {
    @page { size: A4 portrait; margin: 10mm; }
    body { background-color: #fff !important; font-size: 11pt; }
    [data-testid="stSidebar"], .stButton, header, footer, .stDownloadButton, [data-testid="stHeader"], .stTabs {
        display: none !important;
    }
    .main .block-container { padding: 0 !important; margin: 0 !important; width: 100% !important; }
    .a4-container { border: none !important; padding: 0 !important; width: 100% !important; box-shadow: none !important; }
}
</style>
""", unsafe_allow_html=True)

# Veritabanı Mimarisi
conn = sqlite3.connect('art_dizayn_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS musteriler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_adi TEXT, yetkili TEXT, telefon TEXT, adres TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS teklifler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, teklif_no TEXT, musteri_adi TEXT, yetkili TEXT, telefon TEXT, 
              tarih TEXT, kalemler_json TEXT, ara_toplam REAL, kdv REAL, genel_toplam REAL, durum TEXT, sartlar TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS isler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, musteri_id INTEGER, isin_cinsi TEXT, toplam_tutar REAL, tarih TEXT, montaj_tarihi TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS kasa 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, tip TEXT, kategori TEXT, tutar REAL, tarih TEXT, aciklama TEXT)''')

conn.commit()

# Oturum Durumları
if 'teklif_kalemleri' not in st.session_state:
    st.session_state.teklif_kalemleri = []

def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        pd.read_sql_query("SELECT * FROM musteriler", conn).to_excel(writer, sheet_name='Müşteriler', index=False)
        pd.read_sql_query("SELECT * FROM teklifler", conn).to_excel(writer, sheet_name='Verilen Teklifler', index=False)
        pd.read_sql_query("SELECT * FROM kasa", conn).to_excel(writer, sheet_name='Kasa Defteri', index=False)
    return output.getvalue()

st.title("🏗️ ART DİZAYN - Yönetim & Finans ERP")

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.caption("PVC, Alüminyum, Cam Balkon & Çelik Sistemleri Mobil ERP")
with col_head2:
    st.download_button(
        label="📊 Excel Raporu İndir",
        data=to_excel(),
        file_name=f"ART_DIZAYN_Rapor_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.markdown("---")

tab_teklif_olustur, tab_verilen_teklifler, tab_kasa, tab_musteri, tab_hesap, tab_takvim = st.tabs([
    "📄 Teklif Oluştur",
    "📑 Verilen Teklifler",
    "💰 Kasa & Gider Defteri",
    "👤 Müşteri Yönetimi", 
    "📏 Ölçü & Metraj Motoru",
    "🗓️ Şantiye Takvimi"
])

# ---------------------------------------------------------
# 1. TEKLİF FORMUNU OLUŞTURMA
# ---------------------------------------------------------
with tab_teklif_olustur:
    st.subheader("📄 Kurumsal Teklif Hazırlama")
    col_tf1, col_tf2 = st.columns([1, 1])
    
    with col_tf1:
        st.write("**Müşteri ve Teklif Bilgileri**")
        uploaded_logo = st.file_uploader("Firma Logosu Yükle", type=["png", "jpg", "jpeg"])
        logo_base64 = f"data:image/png;base64,{base64.b64encode(uploaded_logo.getvalue()).decode()}" if uploaded_logo else ""
            
        tf_musteri = st.text_input("Müşteri / Firma Adı", "Örnek İnşaat Ltd. Şti.")
        tf_yetkili = st.text_input("Yetkili Kişi", "Ahmet Yılmaz")
        tf_tel = st.text_input("Telefon", "+90 532 000 00 00")
        tf_no = st.text_input("Teklif No", f"ART-{datetime.now().strftime('%Y%m%d')}-{len(pd.read_sql_query('SELECT id FROM teklifler', conn))+1:02d}")
        tf_tarih = st.date_input("Teklif Tarihi", value=date.today())
        
        st.markdown("---")
        st.write("**Kalem Ekleme**")
        kalem_aciklama = st.text_input("Ürün / Hizmet Açıklaması", "8mm Füme Camlı Isıcamlı Balkon Kapatma Sistemi")
        c_k1, c_k2, c_k3 = st.columns(3)
        kalem_miktar = c_k1.number_input("Miktar", value=15.0, step=1.0)
        kalem_birim = c_k2.selectbox("Birim", ["m²", "Metre", "Adet", "Set", "Kg"])
        kalem_fiyat = c_k3.number_input("Birim Fiyat (TL)", value=3500.0, step=100.0)
        
        if st.button("➕ Kalemi Listeye Ekle", use_container_width=True):
            st.session_state.teklif_kalemleri.append({
                "Sıra": len(st.session_state.teklif_kalemleri) + 1,
                "Açıklama": kalem_aciklama,
                "Miktar": kalem_miktar,
                "Birim": kalem_birim,
                "Birim Fiyat": kalem_fiyat,
                "Toplam Tutar": kalem_miktar * kalem_fiyat
            })
            st.rerun()
            
        if st.button("🗑️ Kalemleri Temizle"):
            st.session_state.teklif_kalemleri = []
            st.rerun()

        tf_sartlar = st.text_area("Teklif Koşulları", 
"""1. Bu teklif verildiği tarihten itibaren 15 gün geçerlidir.
2. Ödeme: %50 Siparişte, %50 Montaj tesliminde tahsil edilir.
3. Teslimat süresi ölçü alımından itibaren 10 iş günüdür.
4. Ürünlerimiz 2 yıl sızdırmazlık ve mekanizma garantilidir.""", height=100)

    with col_tf2:
        st.write("**Form Önizleme & Kayıt**")
        logo_html = f'<img src="{logo_base64}" style="max-height: 50px;">' if logo_base64 else '<h2 style="color:#0F2C59; margin:0;">ART DİZAYN</h2>'
        
        table_rows_html = ""
        ara_toplam = 0.0
        for item in st.session_state.teklif_kalemleri:
            ara_toplam += item["Toplam Tutar"]
            table_rows_html += f"""<tr style="border-bottom: 1px solid #e2e8f0; font-size: 11px;">
                <td style="padding: 6px; text-align: center;">{item['Sıra']}</td>
                <td style="padding: 6px;">{item['Açıklama']}</td>
                <td style="padding: 6px; text-align: center;">{item['Miktar']} {item['Birim']}</td>
                <td style="padding: 6px; text-align: right;">{item['Birim Fiyat']:,.2f} TL</td>
                <td style="padding: 6px; text-align: right; font-weight: bold;">{item['Toplam Tutar']:,.2f} TL</td>
            </tr>"""
            
        kdv_tutar = ara_toplam * 0.20
        genel_toplam = ara_toplam + kdv_tutar
        
        teklif_html_full = f"""<div class="a4-container" style="border: 1px solid #cbd5e1; padding: 20px; border-radius: 6px; background-color: #ffffff; color: #0f172a;">
            <table style="width: 100%; border-collapse: collapse; border-bottom: 2px solid #0F2C59; padding-bottom: 8px;">
                <tr>
                    <td style="vertical-align: middle;">{logo_html}<br><span style="font-size:9px; color:#475569;">ALÜMİNYUM & PVC SİSTEMLERİ</span></td>
                    <td style="text-align: right; vertical-align: middle;">
                        <h4 style="margin:0; color: #0F2C59;">TEKLİF FORMU</h4>
                        <span style="font-size: 10px; color: #475569;"><b>No:</b> {tf_no} | <b>Tarih:</b> {tf_tarih.strftime('%d.%m.%Y')}</span>
                    </td>
                </tr>
            </table>
            <div style="background-color: #f8fafc; border-left: 3px solid #0F2C59; padding: 8px; margin: 10px 0; font-size: 11px;">
                <b>Müşteri:</b> {tf_musteri} | <b>Yetkili:</b> {tf_yetkili} | <b>Tel:</b> {tf_tel}
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                <thead>
                    <tr style="background-color: #0F2C59; color: #ffffff; font-size: 11px;">
                        <th style="padding: 6px;">#</th><th style="padding: 6px; text-align: left;">Açıklama</th><th style="padding: 6px;">Miktar</th><th style="padding: 6px; text-align: right;">B.Fiyat</th><th style="padding: 6px; text-align: right;">Toplam</th>
                    </tr>
                </thead>
                <tbody>{table_rows_html if table_rows_html else '<tr><td colspan="5" style="text-align:center; padding:10px; font-size:11px;">Kalem bulunmuyor.</td></tr>'}</tbody>
            </table>
            <table style="width: 220px; margin-left: auto; border-collapse: collapse; font-size: 11px;">
                <tr><td>Ara Toplam:</td><td style="text-align: right;"><b>{ara_toplam:,.2f} TL</b></td></tr>
                <tr><td>KDV (%20):</td><td style="text-align: right;"><b>{kdv_tutar:,.2f} TL</b></td></tr>
                <tr style="border-top: 2px solid #0F2C59; color: #0F2C59;"><td><b>GENEL TOPLAM:</b></td><td style="text-align: right;"><b>{genel_toplam:,.2f} TL</b></td></tr>
            </table>
            <div style="margin-top: 15px; border-top: 1px solid #e2e8f0; padding-top: 5px; font-size: 9px; color: #475569;">
                <b>ŞARTLAR:</b><br>{tf_sartlar.replace('\n', '<br>')}
            </div>
        </div>"""
        
        st.markdown(teklif_html_full, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("💾 Teklifi Hafızaya Kaydet", use_container_width=True):
            import json
            kalemler_str = json.dumps(st.session_state.teklif_kalemleri)
            c.execute("""INSERT INTO teklifler 
                (teklif_no, musteri_adi, yetkili, telefon, tarih, kalemler_json, ara_toplam, kdv, genel_toplam, durum, sartlar) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tf_no, tf_musteri, tf_yetkili, tf_tel, tf_tarih.strftime('%Y-%m-%d'), kalemler_str, ara_toplam, kdv_tutar, genel_toplam, 'Beklemede', tf_sartlar))
            conn.commit()
            st.success("Teklif başarıyla hafızaya kaydedildi!")

# ---------------------------------------------------------
# 2. VERİLEN TEKLİFLER VE ONAYLAMA
# ---------------------------------------------------------
with tab_verilen_teklifler:
    st.subheader("📑 Verilen Teklifler Hafızası")
    df_teklifler = pd.read_sql_query("SELECT id, teklif_no as 'Teklif No', musteri_adi as 'Müşteri', genel_toplam as 'Tutar (TL)', durum as 'Durum', tarih as 'Tarih' FROM teklifler ORDER BY id DESC", conn)
    
    if not df_teklifler.empty:
        st.dataframe(df_teklifler, use_container_width=True)
        
        selected_teklif_id = st.selectbox("İşlem Yapılacak Teklifi Seçin", df_teklifler['id'].tolist(), format_func=lambda x: f"Teklif ID: {x}")
        
        col_t_act1, col_t_act2, col_t_act3 = st.columns(3)
        
        with col_t_act1:
            if st.button("✅ Teklifi Onayla ve Kasaya Aktar", use_container_width=True):
                row = pd.read_sql_query(f"SELECT * FROM teklifler WHERE id={selected_teklif_id}", conn).iloc[0]
                c.execute("UPDATE teklifler SET durum='Onaylandı' WHERE id=?", (selected_teklif_id,))
                c.execute("INSERT INTO kasa (tip, kategori, tutar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)",
                          ('Gelir', 'Onaylanan Teklif', row['genel_toplam'], datetime.now().strftime('%Y-%m-%d'), f"Teklif Onayı: {row['teklif_no']} - {row['musteri_adi']}"))
                conn.commit()
                st.success("Teklif onaylandı ve tutar Kasa Defterine Gelir olarak eklendi!")
                st.rerun()

        with col_t_act2:
            row_wa = pd.read_sql_query(f"SELECT * FROM teklifler WHERE id={selected_teklif_id}", conn).iloc[0]
            wa_msg = f"Sayın {row_wa['musteri_adi']},\n{row_wa['teklif_no']} nolu teklif tutarınız: {row_wa['genel_toplam']:,.2f} TL'dir."
            wa_url = f"https://wa.me/{str(row_wa['telefon']).replace('+','').replace(' ','')}?text={urllib.parse.quote(wa_msg)}"
            st.markdown(f"[📲 WhatsApp ile Tekrar Gönder]({wa_url})")

        with col_t_act3:
            if st.button("❌ Teklifi Sil", use_container_width=True):
                c.execute("DELETE FROM teklifler WHERE id=?", (selected_teklif_id,))
                conn.commit()
                st.warning("Teklif silindi!")
                st.rerun()
    else:
        st.info("Kayıtlı teklif bulunmamaktadır.")

# ---------------------------------------------------------
# 3. KASA & GİDER DEFTERİ
# ---------------------------------------------------------
with tab_kasa:
    st.subheader("💰 Genel Kasa, Personel & Gider Defteri")
    
    col_k1, col_k2 = st.columns([1, 2])
    
    with col_k1:
        st.write("### ➕ Gelir / Gider Ekle")
        k_tip = st.selectbox("İşlem Tipi", ["Gider", "Gelir"])
        k_kat = st.selectbox("Kategori", ["Eleman Maaşı / Avans", "Yemek / Yol", "Malzeme Alımı", "Kira / Fatura", "Müşteri Tahsilatı", "Diğer"])
        k_tutar = st.number_input("Tutar (TL)", value=500.0, step=100.0)
        k_aciklama = st.text_input("Açıklama", "Ahmet Usta Avans")
        k_tarih = st.date_input("İşlem Tarihi", value=date.today())
        
        if st.button("💾 Kasaya İşle", use_container_width=True):
            c.execute("INSERT INTO kasa (tip, kategori, tutar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)",
                      (k_tip, k_kat, k_tutar, k_tarih.strftime('%Y-%m-%d'), k_aciklama))
            conn.commit()
            st.success("Kasa kaydı eklendi!")
            st.rerun()

    with col_k2:
        df_kasa = pd.read_sql_query("SELECT id, tip as 'Tip', kategori as 'Kategori', tutar as 'Tutar (TL)', tarih as 'Tarih', aciklama as 'Açıklama' FROM kasa ORDER BY id DESC", conn)
        
        toplam_gelir = df_kasa[df_kasa['Tip'] == 'Gelir']['Tutar (TL)'].sum() if not df_kasa.empty else 0.0
        toplam_gider = df_kasa[df_kasa['Tip'] == 'Gider']['Tutar (TL)'].sum() if not df_kasa.empty else 0.0
        net_durum = toplam_gelir - toplam_gider
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Toplam Gelir", f"{toplam_gelir:,.2f} TL")
        c_m2.metric("Toplam Gider", f"{toplam_gider:,.2f} TL")
        c_m3.metric("Net Kasa Bakiyesi", f"{net_durum:,.2f} TL")
        
        st.dataframe(df_kasa, use_container_width=True)

# ---------------------------------------------------------
# 4. MÜŞTERİ YÖNETİMİ (SİLME ÖZELLİĞİ EKLENDİ)
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Cari Yönetimi & Silme")
    col_m1, col_m2 = st.columns([1, 2])
    
    with col_m1:
        st.write("### ➕ Yeni Müşteri")
        f_adi = st.text_input("Firma / Müşteri Adı*")
        y_adi = st.text_input("Yetkili Adı")
        tel = st.text_input("Müşteri Telefon", "+905320000000")
        adr = st.text_area("Adres")
        
        if st.button("💾 Müşteriyi Kaydet", use_container_width=True):
            if f_adi.strip():
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)", (f_adi, y_adi, tel, adr))
                conn.commit()
                st.success("Müşteri kaydedildi!")
                st.rerun()

    with col_m2:
        st.write("### 🔍 Kayıtlı Müşteriler")
        df_m = pd.read_sql_query("SELECT id as 'ID', firma_adi as 'Firma', yetkili as 'Yetkili', telefon as 'Telefon', adres as 'Adres' FROM musteriler", conn)
        st.dataframe(df_m, use_container_width=True)
        
        if not df_m.empty:
            st.markdown("---")
            st.write("### 🗑️ Müşteri Silme İşlemi")
            sil_id = st.selectbox("Sistemden Çıkarılacak Müşteriyi Seçin", df_m['ID'].tolist(), format_func=lambda x: f"ID: {x} - {df_m[df_m['ID']==x]['Firma'].values[0]}")
            if st.button("❌ Müşteriyi Sistemden Kalıcı Olarak Sil", use_container_width=True):
                c.execute("DELETE FROM musteriler WHERE id=?", (sil_id,))
                conn.commit()
                st.warning("Müşteri sistemden silindi!")
                st.rerun()

# ---------------------------------------------------------
# 5. GELİŞMİŞ ÖLÇÜ & METRAJ MOTORU
# ---------------------------------------------------------
with tab_hesap:
    st.subheader("📏 Otomatik İmalat Ölçü & Metraj Hesabı")
    
    urun_tipi = st.selectbox("İmalat / Ürün Tipi Seçin", [
        "Cam Balkon Sistemi", 
        "Alüminyum Korkuluk / Küpeşte", 
        "Çelik Çatı / Taşıyıcı Karkas", 
        "PVC Doğrama Pencere/Kapı",
        "Pergola / Veranda"
    ])
    
    col_h1, col_h2 = st.columns(2)
    en_cm = col_h1.number_input("Genişlik / En (cm)", value=300.0, step=10.0)
    boy_cm = col_h2.number_input("Yükseklik / Boy (cm)", value=200.0, step=10.0)
    
    m2 = (en_cm / 100) * (boy_cm / 100)
    cevre_m = ((en_cm + boy_cm) * 2) / 100
    
    st.markdown("---")
    st.write(f"### 📊 Metraj Analiz Raporu: **{urun_tipi}**")
    
    if urun_tipi == "Cam Balkon Sistemi":
        kanat_sayisi = round((en_cm / 60))
        st.write(f"* **Toplam Cam Alanı:** {m2:.2f} m²")
        st.write(f"* **Önerilen Kanat Sayısı:** {kanat_sayisi} Kanat (Ortalama 60 cm genişlik)")
        st.write(f"* **Kasa & Baza Profil İhtiyacı:** {cevre_m:.2f} Metre")
    
    elif urun_tipi == "Alüminyum Korkuluk / Küpeşte":
        dikme_sayisi = round(en_cm / 100) + 1
        emniyet_hat_m = (en_cm / 100) * 3
        st.write(f"* **Üst Küpeşte Profili:** {en_cm/100:.2f} Metre")
        st.write(f"* **Tahmini Dikme Sayısı:** {dikme_sayisi} Adet (100 cm aralıkla)")
        st.write(f"* **Emniyet Şeridi (3 Hat):** {emniyet_hat_m:.2f} Metre")
        
    elif urun_tipi == "Çelik Çatı / Taşıyıcı Karkas":
        profil_metraj = ((en_cm / 100) * 5) + ((boy_cm / 100) * 5)
        st.write(f"* **Kaplama Alanı:** {m2:.2f} m²")
        st.write(f"* **Tahmini Steel Kutu Profil İhtiyacı:** ~{profil_metraj:.2f} Metre")
        st.write(f"* **Kapatma Panel İhtiyacı (%10 Fire):** {m2 * 1.10:.2f} m²")

    elif urun_tipi in ["PVC Doğrama Pencere/Kapı", "Pergola / Veranda"]:
        st.write(f"* **Toplam Alan:** {m2:.2f} m²")
        st.write(f"* **Çevre Dış Kasa Metrajı:** {cevre_m:.2f} Metre")

# ---------------------------------------------------------
# 6. ŞANTİYE TAKVİMİ
# ---------------------------------------------------------
with tab_takvim:
    st.subheader("🗓️ Şantiye & Montaj Programı")
    st.info("Müşterilere bağlanan montaj günleri bu ekranda otomatik listelenir.")
