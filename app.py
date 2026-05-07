import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from streamlit_qrcode_scanner import qrcode_scanner
import time

# 1. Konfigurasi Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("Database_Qurban_MAR").get_worksheet(0)

st.set_page_config(page_title="Check-In Masjid Ar-Rahmah", layout="centered")

# --- CSS TEMA PUTIH (LINCAH) ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff !important; }
    .header-masjid { color: #d32f2f; font-weight: 900; font-size: 26px; margin-bottom: -5px; text-align: center; }
    .sub-header { color: #555; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 20px; }
    div[data-testid="stMetricValue"] { color: #2e7d32 !important; font-weight: 800 !important; }
    div.stButton > button { width: 100%; border-radius: 10px !important; height: 3.5em !important; font-weight: bold !important; }
    .info-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #ddd; border-left: 8px solid #1a237e; color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center;'>MASJID AR-RAHMAH</h2>", unsafe_allow_html=True)
st.markdown('<p class="header-masjid">PANITIA QURBAN</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">SISTEM CHECK-IN QURBAN DIGITAL</p>', unsafe_allow_html=True)

# --- DASHBOARD STATISTIK ---
all_data = sheet.get_all_values()
rows = all_data[1:]
total_reg = len(rows)
sudah_ambil = len([row for row in rows if len(row) > 7 and row[7] == "Sudah"])
belum_ambil = total_reg - sudah_ambil

col1, col2, col3 = st.columns(3)
col1.metric("Sudah Ambil", sudah_ambil)
col2.metric("Belum Ambil", belum_ambil)
col3.metric("Total", total_reg)

st.divider()

# --- STATE MANAGEMENT ---
if "step" not in st.session_state: st.session_state.step = "pilih_metode"
if "id_target" not in st.session_state: st.session_state.id_target = None

def reset():
    st.session_state.step = "pilih_metode"
    st.session_state.id_target = None
    st.rerun()

# --- ALUR LOGIKA ---
if st.session_state.step == "pilih_metode":
    c1, c2 = st.columns(2)
    if c1.button("📸 SCAN QR CODE"):
        st.session_state.step = "proses_scan"
        st.rerun()
    if c2.button("✍️ INPUT MANUAL"):
        st.session_state.step = "proses_manual"
        st.rerun()

elif st.session_state.step == "proses_scan":
    id_scan = qrcode_scanner(key='scanner')
    if id_scan:
        st.session_state.id_target = id_scan
        st.session_state.step = "tampil_data"
        st.rerun()
    if st.button("⬅️ Kembali"): reset()

elif st.session_state.step == "proses_manual":
    id_input = st.text_input("Masukkan ID Kupon:").upper()
    if st.button("CARI DATA"):
        if id_input:
            st.session_state.id_target = id_input
            st.session_state.step = "tampil_data"
            st.rerun()
    if st.button("⬅️ Kembali"): reset()

# --- PROSES VERIFIKASI ---
elif st.session_state.step in ["tampil_data", "sukses"] and st.session_state.id_target:
    try:
        cell = sheet.find(st.session_state.id_target)
        row_num = cell.row
        data = sheet.row_values(row_num)

        # REVISI INDEKS KOLOM DISINI:
        email = data[1]
        nama = data[2]
        nik = data[3]
        alamat = data[5]
        status_db = data[7] if len(data) > 7 else "Belum"

        st.markdown(f"""
            <div class="info-card">
                <small style="color: #d32f2f;">ID KUPON: {st.session_state.id_target}</small>
                <h2 style="margin: 0; color: #1a237e;">{nama}</h2>
                <p style="margin: 5px 0;">📍 {alamat} | 🆔 {nik}</p>
                <small style="color: #555;">📧 {email}</small>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.step == "sukses":
            st.success("✅ BERHASIL: Daging Sudah Diambil")
            if st.button("➕ INPUT KUPON BARU", type="primary"): reset()

        elif status_db == "Sudah":
            st.warning(f"⚠️ Daging Sudah Diambil Pada Pukul {data[8] if len(data) > 8 else '-'}")
            if st.button("⬅️ KEMBALI"): reset()

        else:
            st.info("🟢 STATUS: BELUM DIAMBIL")
            if st.button("✔️ KONFIRMASI PENGAMBILAN", type="primary"):
                target_sekarang = st.session_state.id_target
                waktu = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S")
                sheet.update_cell(row_num, 8, "Sudah")
                sheet.update_cell(row_num, 9, waktu)

                st.session_state.id_target = target_sekarang
                st.session_state.step = "sukses"
                time.sleep(0.2)
                st.rerun()

    except Exception:
        if st.session_state.step == "sukses":
            st.success("✅ PROSES SELESAI")
            if st.button("➕ INPUT KUPON BARU", type="primary"): reset()
        else:
            st.error(f"ID '{st.session_state.id_target}' tidak ditemukan.")
            if st.button("⬅️ COBA LAGI"): reset()
