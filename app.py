import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import requests  
from google import genai

# --- MESIN HITUNG TARIF AIR (PAM JAYA KELOMPOK IV A) ---
def hitung_tarif_pdam(liter):
    m3 = liter / 1000.0 # Ubah air dari liter menjadi kubik
    if m3 == 0: return 0
    
    # Hitungan berjenjang seperti anak tangga
    if m3 <= 10:
        biaya = m3 * 6825
    elif m3 <= 20:
        biaya = (10 * 6825) + ((m3 - 10) * 8150)
    else:
        biaya = (10 * 6825) + (10 * 8150) + ((m3 - 20) * 9800)
        
    return biaya

# --- 1. MENGHUBUNGKAN KE AWAN FIREBASE (KUNCI GANDA) ---
if not firebase_admin._apps:
    try:
        try:
            kunci_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(kunci_dict)
        except:
            cred = credentials.Certificate("firebasekey.json")
            
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://water-monitoring-system-e890a-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        st.error(f"Yah, gagal terhubung ke awan Firebase: {e}")

# --- 2. MENGHUBUNGKAN KE OTAK ROBOT AI (GEMINI) ---
try:
    kunci_ai = st.secrets["api_keys"]["kunci_gemini"]
    client = genai.Client(api_key=kunci_ai)
except Exception as e:
    st.warning("⚠️ Kunci AI belum dipasang. Robot AI sedang tidur.")

# --- 3. FUNGSI TUKANG POS TELEGRAM ---
def kirim_telegram(pesan):
    try:
        token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan}
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Aduh, Tukang Pos Error karena ini: {e}")

# --- 4. MEMORI ANTI BERISIK TELEGRAM ---
if 'alarm_gedung_bunyi' not in st.session_state:
    st.session_state.alarm_gedung_bunyi = False
if 'alarm_pengisian_bunyi' not in st.session_state:
    st.session_state.alarm_pengisian_bunyi = False
if 'alarm_toren_kritis_bunyi' not in st.session_state:
    st.session_state.alarm_toren_kritis_bunyi = False

st.set_page_config(page_title="Smart Water Monitoring System", layout="wide")
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>💧 Water Monitoring System 💧</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>Asisten Pintar Penjaga Air Gedung</p>", unsafe_allow_html=True)

# ==============================================================
# 🤖 FITUR CHATBOT AI (DI SEBELAH KIRI LAYAR)
# ==============================================================
st.sidebar.header("🤖 AI Water Assistant")
st.sidebar.write("Tanya aku tentang keadaan air atau pintu keran!")

if "ingatan_chat" not in st.session_state:
    st.session_state.ingatan_chat = []

wadah_chat = st.sidebar.container(height=500, border=False)

for pesan in st.session_state.ingatan_chat:
    with wadah_chat.chat_message(pesan["siapa"]):
        st.markdown(pesan["teks"])

pertanyaan_baru = st.sidebar.chat_input("Tanya di sini (Cth: Kenapa tagihan hari ini melonjak?)")

if pertanyaan_baru:
    with wadah_chat.chat_message("user"):
        st.markdown(pertanyaan_baru)
    st.session_state.ingatan_chat.append({"siapa": "user", "teks": pertanyaan_baru})

    # Mengambil seluruh data real-time, anomali, dan buku harian data log untuk diserahkan ke AI
    data_sensors = db.reference('/sensors').get() or {}
    data_actuators = db.reference('/actuators').get() or {}
    data_sejarah = db.reference('/history_pemakaian').get() or {}
    data_anomali = db.reference('/logs/anomaly').get() or {}
    
    volume_pdam_liter = data_sensors.get('kincir_7', {}).get('total_liter', 0)
    estimasi_tagihan = hitung_tarif_pdam(volume_pdam_liter)
    
    # Paket data komparatif super lengkap untuk analisa AI Gemini
    data_keseluruhan = {
        "SENSOR_AIR_REALTIME": data_sensors,
        "MESIN_DAN_PINTU_AIR": data_actuators,
        "TAGIHAN_PDAM_SAAT_INI": f"Rp {estimasi_tagihan:,.0f}".replace(',', '.'),
        "STATUS_GANGGUAN_ANOMALI": data_anomali,
        "BUKU_HARIAN_LOG_SEJARAH_AIR": data_sejarah 
    }

    bisikan_rahasia = f"""
    Kamu adalah asisten pintar yang menjaga air gedung. 
    Gunakan bahasa yang sangat mudah dimengerti, ramah, dan seru!
    
    ATURAN PENTING:
    1. Data pada 'SENSOR_AIR_REALTIME' dan 'TAGIHAN_PDAM_SAAT_INI' adalah pemakaian KHUSUS HARI INI SAJA (selalu di-reset menjadi 0 setiap jam 00:00 tengah malam).
    2. Jika user bertanya "Berapa pemakaian hari ini?", langsung ambil dari SENSOR_AIR_REALTIME.
    3. Jika user bertanya tentang hari kemarin, bulan lalu, atau riwayat waktu lainnya, kamu WAJIB menganalisis data di bagian 'BUKU_HARIAN_LOG_SEJARAH_AIR'.
    4. Periksa 'STATUS_GANGGUAN_ANOMALI' untuk melihat apakah PDAM sedang bermasalah.
    
    DATA SAAT INI: {data_keseluruhan}
    
    Pertanyaan: "{pertanyaan_baru}"
    """

    with wadah_chat.chat_message("assistant"):
        with st.spinner("Hmm, sebentar ya aku liat buku harian data dulu..."):
            try:
                jawaban_robot = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=bisikan_rahasia
                )
                st.markdown(jawaban_robot.text)
                st.session_state.ingatan_chat.append({"siapa": "assistant", "teks": jawaban_robot.text})
            except Exception as e:
                st.error("Duh, AI lagi ngantuk nih.")

# ==============================================================
# 🕹️ RUANG KENDALI PINTU AIR (VALVE)
# ==============================================================
st.subheader("🕹️ Remote Control Pintu Air")

ref_actuators = db.reference('/actuators')
data_actuators = ref_actuators.get() or {}

status_v1 = data_actuators.get('valve_lantai_1', 'TUTUP')
status_v2 = data_actuators.get('valve_lantai_2', 'TUTUP')
status_v3 = data_actuators.get('valve_lantai_3', 'TUTUP')

kolom_v1, kolom_v2, kolom_v3 = st.columns(3)

with kolom_v1:
    st.markdown("### 🏢 Lantai 1")
    if st.button("🔄 Tekan untuk Ubah Lantai 1", key="btn_v1"):
        posisi_baru = 'BUKA' if status_v1 == 'TUTUP' else 'TUTUP'
        ref_actuators.update({'valve_lantai_1': posisi_baru})
        st.rerun()
    if status_v1 == 'BUKA':
        st.success("Air Mengalir! 🟢")
    else:
        st.error("Air Berhenti 🔴")

with kolom_v2:
    st.markdown("### 🏢 Lantai 2")
    if st.button("🔄 Tekan untuk Ubah Lantai 2", key="btn_v2"):
        posisi_baru = 'BUKA' if status_v2 == 'TUTUP' else 'TUTUP'
        ref_actuators.update({'valve_lantai_2': posisi_baru})
        st.rerun()
    if status_v2 == 'BUKA':
        st.success("Air Mengalir! 🟢")
    else:
        st.error("Air Berhenti 🔴")

with kolom_v3:
    st.markdown("### 🏢 Lantai 3")
    if st.button("🔄 Tekan untuk Ubah Lantai 3", key="btn_v3"):
        posisi_baru = 'BUKA' if status_v3 == 'TUTUP' else 'TUTUP'
        ref_actuators.update({'valve_lantai_3': posisi_baru})
        st.rerun()
    if status_v3 == 'BUKA':
        st.success("Air Mengalir! 🟢")
    else:
        st.error("Air Berhenti 🔴")

st.divider()

# ==============================================================
# 📊 LAYAR TV PEMANTAUAN OTOMATIS
# ==============================================================
layar_utama = st.empty()

while True:
    data_sensors = db.reference('/sensors').get() or {}
    data_actuators = db.reference('/actuators').get() or {}
    data_anomali = db.reference('/logs/anomaly').get() or {}

    with layar_utama.container():
        s1, s2, s3 = data_sensors.get('kincir_1', {}), data_sensors.get('kincir_2', {}), data_sensors.get('kincir_3', {})
        s4, s5 = data_sensors.get('kincir_4', {}), data_sensors.get('kincir_5', {})
        s6, s7 = data_sensors.get('kincir_6', {}), data_sensors.get('kincir_7', {})

        # ==============================================================
        # 1. PENGGUNAAN AIR DI DALAM GEDUNG
        # ==============================================================
        st.subheader("🏢 Penggunaan Air di Dalam Gedung")
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown("#### Lantai 1")
            st.metric("Debit Air", f"{s1.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s1.get('total_liter', 0):.2f} Liter")
        with k2:
            st.markdown("#### Lantai 2")
            st.metric("Debit Air", f"{s2.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s2.get('total_liter', 0):.2f} Liter")
        with k3:
            st.markdown("#### Lantai 3")
            st.metric("Debit Air", f"{s3.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s3.get('total_liter', 0):.2f} Liter")
        with k4:
            st.markdown("#### Keluar Toren Atas")
            st.metric("Debit Air", f"{s4.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s4.get('total_liter', 0):.2f} Liter")

        st.divider()

        # ==============================================================
        # 2. JALUR PENGISIAN & PDAM
        # ==============================================================
        st.subheader("⬆️ Jalur Pengisian & PDAM")
        k5, k6, k7 = st.columns(3)
        
        with k5:
            st.markdown("#### Pipa Naik (Dari Bawah)")
            st.metric("Debit Air", f"{s5.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s5.get('total_liter', 0):.2f} Liter")
        with k6:
            st.markdown("#### Pipa Naik (Sampai Atas)")
            st.metric("Debit Air", f"{s6.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{s6.get('total_liter', 0):.2f} Liter")
        with k7:
            st.markdown("#### Air Masuk PDAM")
            vol_pdam = s7.get('total_liter', 0)
            st.metric("Debit Air", f"{s7.get('debit', 0):.2f} L/min")
            st.metric("Volume Total", f"{vol_pdam:.2f} Liter")

        st.divider()

        # ==============================================================
        # 3. KOLOM KHUSUS ESTIMASI TAGIHAN & STATUS PASOKAN UTAMA
        # ==============================================================
        st.subheader("💰 Estimasi Tagihan Air PDAM (Kantor/Komersial)")
        biaya_pdam = hitung_tarif_pdam(vol_pdam)
        kubik_air = vol_pdam / 1000.0
        
        # Mengambil status evaluasi waktu pengisian PDAM dari ESP32
        status_pdam_pusat = data_anomali.get('pdam_status', 'AMAN')
        
        kolom_uang1, kolom_uang2 = st.columns(2)
        with kolom_uang1:
            st.metric("Total Pemakaian (Meter Kubik)", f"{kubik_air:.3f} m³")
        with kolom_uang2:
            st.metric("Estimasi Biaya Berjalan", f"Rp {biaya_pdam:,.0f}".replace(',', '.'))
            
        # Tampilan kotak status cerdas deteksi pasokan PDAM macet
        if status_pdam_pusat == "BERMASALAH":
            st.error("⚠️ STATUS PASOKAN: PDAM BERMASALAH! (Aliran air macet/drop karena pompa aktif > 3 menit tapi air tidak naik)")
        else:
            st.success("✅ STATUS PASOKAN: PDAM AMAN (Aliran air lancar masuk ke dalam tangki)")

        st.divider()

        # ==============================================================
        # 4. TINGGI AIR DI TANGKI
        # ==============================================================
        st.subheader("📊 Tinggi Air di Tangki")
        t1, t2, t3, t4 = st.columns(4)
        
        jarak_bawah = data_sensors.get('jarak_toren_bawah', 0)
        t1.metric("Toren Bawah", f"{jarak_bawah} cm")
        t2.metric("Toren Atas", f"{data_sensors.get('jarak_toren_atas', 0)} cm")
        
        if jarak_bawah > 40:  
            t3.error("Pompa Naik: MATI (Air Kering) 🛑")
            if not st.session_state.alarm_toren_kritis_bunyi:
                kirim_telegram("🚨 DANGER! Toren bawah kosong. Pompa dimatikan!")
                st.session_state.alarm_toren_kritis_bunyi = True
        else:
            if data_actuators.get('pompa_naik') == 'NYALA':
                t3.success("Pompa Naik: NYALA 🟢")
            else:
                t3.error("Pompa Naik: MATI 🔴")
            st.session_state.alarm_toren_kritis_bunyi = False

        if data_actuators.get('pompa_pdam') == 'NYALA':
            t4.success("Pompa PDAM: NYALA 🟢")
        else:
            t4.error("Pompa PDAM: MATI 🔴")

        st.divider()

        # ==============================================================
        # 5. PEMERIKSAAN KUALITAS AIR
        # ==============================================================
        st.subheader("🔬 Pemeriksaan Kualitas Air")
        q1, q2, q3 = st.columns(3)
        q1.metric("Kotoran Toren Bawah (TDS)", f"{data_sensors.get('tds_bawah', 0)} ppm")
        q2.metric("Kotoran Toren Atas (TDS)", f"{data_sensors.get('tds_atas', 0)} ppm")
        q3.metric("Suhu Air Toren Atas", f"{data_sensors.get('suhu', 0.0)} °C")
        
        st.divider()

        # ==============================================================
        # 6. ALARM KEAMANAN
        # ==============================================================
        st.subheader("🚨 Alarm Keamanan")
        kolom_alarm1, kolom_alarm2 = st.columns(2)
        
        with kolom_alarm1:
            air_dipakai = s1.get('debit', 0) + s2.get('debit', 0) + s3.get('debit', 0)
            air_hilang_gedung = s4.get('debit', 0) - air_dipakai
            
            if air_hilang_gedung > 1:
                st.error("Gawat! Ada pipa bocor di dalam gedung! 💦")
                if not st.session_state.alarm_gedung_bunyi:
                    kirim_telegram("🚨 Bocor di pipa gedung!")
                    st.session_state.alarm_gedung_bunyi = True
            else:
                st.success("Pipa gedung aman ✅")
                st.session_state.alarm_gedung_bunyi = False
                
        with kolom_alarm2:
            air_hilang_pengisian = s5.get('debit', 0) - s6.get('debit', 0)
            if air_hilang_pengisian > 1:
                st.error("Gawat! Ada pipa bocor ke arah toren atas! 💦")
                if not st.session_state.alarm_pengisian_bunyi:
                    kirim_telegram("🚨 Bocor di pipa pengisian toren!")
                    st.session_state.alarm_pengisian_bunyi = True
            else:
                st.success("Pipa ke toren aman ✅")
                st.session_state.alarm_pengisian_bunyi = False

    time.sleep(1)
