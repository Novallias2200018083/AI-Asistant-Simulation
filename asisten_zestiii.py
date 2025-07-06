import tkinter as tk
from tkinter import ttk, scrolledtext
import speech_recognition as sr
from gtts import gTTS
import os
import webbrowser
from datetime import datetime, timedelta
import threading
import time
from playsound import playsound
import requests
import wikipediaapi
import re # Mengimpor modul Regular Expressions

# --- KONFIGURASI DAN INISIALISASI ---
recognizer = sr.Recognizer()
wiki_api = wikipediaapi.Wikipedia('AsistenVirtualZestiii/2.0', 'id')
AUDIO_FILE = "response.mp3"
NOTES_FILE = "catatan_zestiii.txt"
API_KEY_CUACA = "a17333c55a5c4e97906103002240207" # Ganti dengan API Key Anda

# --- MEMORI KONTEKSTUAL ---
konteks_terakhir = {
    "url": "",
    "situs": "",
    "query": "",
    "aksi": ""
}

# --- FUNGSI DASAR & SUPER POWER ---
def bicara(teks, display_log=True):
    print(f"Asisten: {teks}")
    if display_log:
        app.after(0, update_log, f"Asisten: {teks}")
    try:
        tts = gTTS(text=teks, lang='id', slow=False)
        tts.save(AUDIO_FILE)
        playsound(AUDIO_FILE)
    except Exception as e:
        print(f"Gagal memutar audio: {e}")
    finally:
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

def setel_alarm(durasi_detik, pesan):
    def alarm():
        time.sleep(durasi_detik)
        app.after(0, update_status, f"ALARM: {pesan}")
        playsound('https://www.soundjay.com/buttons/sounds/button-7.mp3') # Suara alarm sederhana
        bicara(f"Waktunya untuk {pesan}", display_log=False)
    threading.Thread(target=alarm, daemon=True).start()
    response = f"Baik, alarm untuk '{pesan}' telah disetel {durasi_detik // 60} menit dari sekarang."
    return response

def tulis_catatan(catatan):
    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {catatan}\n")
        return f"Oke, sudah saya catat: '{catatan}'."
    except Exception as e:
        print(f"Gagal menulis catatan: {e}")
        return "Maaf, saya gagal menyimpan catatan."

# --- OTAK ASISTEN: Intent Engine & Context Handler ---
def handle_command(command):
    global konteks_terakhir
    command = command.lower()
    response = ""

    # 1. CEK PERINTAH KONTEKSTUAL (FOLLOW-UP)
    if konteks_terakhir["aksi"] == "cari_situs":
        if "urutkan dari yang termurah" in command:
            if konteks_terakhir["situs"] == "tokopedia":
                url = f"{konteks_terakhir['url']}&sort=9"
                webbrowser.open(url)
                response = "Siap, sudah diurutkan dari harga termurah."
                konteks_terakhir = {} # Reset konteks
                app.after(0, update_log, f"Asisten: {response}")
                app.after(0, bicara, response)
                return

    # 2. MESIN PENCOCOKAN NIAT (INTENT ENGINE)
    # Pola: niat -> ( [daftar kata kunci], fungsi_handler )
    intents = {
        "KELUAR": (['keluar', 'stop', 'selesai'], lambda cmd: "exit"),
        "ALARM": (['alarm', 'timer'], handle_alarm_intent),
        "CATATAN": (['tulis catatan', 'catat', 'ingat ini'], handle_catatan_intent),
        "CARI_SITUS": (['di youtube', 'di spotify', 'di tokopedia', 'di shopee'], handle_pencarian_situs_intent),
        "WIKIPEDIA": (['siapa', 'apa itu', 'wikipedia'], handle_wikipedia_intent),
        "CUACA": (['cuaca di'], handle_cuaca_intent),
        "WAKTU": (['jam berapa', 'tanggal berapa'], handle_waktu_intent),
        "BUKA_SITUS": (['buka'], handle_buka_situs_intent),
        "CARI_GOOGLE": (['cari'], handle_cari_google_intent), # Prioritas terakhir untuk 'cari'
    }

    niat_terdeteksi = None
    for niat, (keywords, handler) in intents.items():
        for keyword in keywords:
            if keyword in command:
                niat_terdeteksi = handler(command)
                break
        if niat_terdeteksi:
            break
    
    if isinstance(niat_terdeteksi, str):
        response = niat_terdeteksi
    elif isinstance(niat_terdeteksi, dict):
        response = niat_terdeteksi.get("response", "Maaf, terjadi kesalahan.")
    else:
        response = "Maaf, saya tidak mengerti. Bisa ulangi lagi?"

    if response == "exit":
        bicara("Tentu, sampai jumpa lagi!")
        app.after(1000, app.quit)
        return
    
    app.after(0, update_log, f"Asisten: {response}")
    app.after(0, bicara, response)


# --- INTENT HANDLERS (FUNGSI-FUNGSI PEMROSESAN PERINTAH) ---
def handle_alarm_intent(command):
    match = re.search(r'(\d+)\s+(menit|detik|jam)', command)
    if match:
        jumlah = int(match.group(1))
        unit = match.group(2)
        durasi_detik = jumlah * 60 if unit == 'menit' else (jumlah * 3600 if unit == 'jam' else jumlah)
        
        pesan_match = re.search(r'(untuk|buat)\s+([^\d]+)', command)
        pesan = pesan_match.group(2).strip() if pesan_match else "waktunya habis"
        
        return setel_alarm(durasi_detik, pesan)
    return "Tentukan durasi alarm. Contoh: 'setel alarm 5 menit untuk istirahat'."

def handle_catatan_intent(command):
    query = command.split('catat')[-1].split('tulis catatan')[-1].split('ingat ini')[-1].strip()
    return tulis_catatan(query)

def handle_pencarian_situs_intent(command):
    global konteks_terakhir
    sites = {'youtube': 'https://www.youtube.com/results?search_query=', 'spotify': 'https://open.spotify.com/search/', 'tokopedia': 'https://www.tokopedia.com/search?q=', 'shopee': 'https://shopee.co.id/search?keyword='}
    for site_name, base_url in sites.items():
        if f"di {site_name}" in command:
            query = command.split('di')[0].replace('cari', '').replace('putar', '').strip()
            encoded_query = requests.utils.quote(query)
            url_to_open = base_url + encoded_query
            webbrowser.open(url_to_open)
            
            # Simpan ke memori konteks
            konteks_terakhir = {"url": url_to_open, "situs": site_name, "query": query, "aksi": "cari_situs"}
            
            return f"Oke, mencari '{query}' di {site_name.capitalize()}."
    return None

def handle_wikipedia_intent(command):
    topik = command.replace('wikipedia', '').replace('siapa itu', '').replace('apa itu', '').strip()
    try:
        page = wiki_api.page(topik)
        return f"Menurut Wikipedia, {page.summary.splitlines()[0]}" if page.exists() else f"Maaf, tidak ada info tentang {topik}."
    except: return "Maaf, layanan Wikipedia bermasalah."

def handle_cuaca_intent(command):
    kota = command.split('cuaca di')[-1].strip()
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_CUACA}&q={kota}&aqi=no"
        data = requests.get(url).json()
        if "error" in data: return f"Maaf, tidak bisa menemukan kota {kota}."
        kondisi, suhu = data['current']['condition']['text'], data['current']['temp_c']
        return f"Cuaca di {kota} saat ini {kondisi} dengan suhu {suhu} derajat Celcius."
    except: return "Maaf, layanan cuaca bermasalah."

def handle_waktu_intent(command):
    now = datetime.now()
    return f"Sekarang jam {now.strftime('%H:%M')}." if 'jam' in command else f"Hari ini tanggal {now.strftime('%d %B %Y')}."

def handle_buka_situs_intent(command):
    website = command.split('buka')[-1].strip().replace(' ', '')
    if '.' not in website: website += ".com"
    webbrowser.open(f"https://www.{website}")
    return f"Baik, membuka {website}."

def handle_cari_google_intent(command):
    query = command.split('cari')[-1].strip()
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Ini hasil pencarian umum untuk '{query}' di Google."

# --- FUNGSI PENDENGAR, GUI, & MAIN LOOP ---
def dengar_dan_proses():
    update_status("Mendengarkan...")
    listen_button.config(state=tk.DISABLED)
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Silakan bicara...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            update_status("Memproses perintah...")
            query = recognizer.recognize_google(audio, language='id-ID')
            print(f"Pengguna: {query}")
            update_log(f"Pengguna: {query}")
            handle_command(query)
        except sr.UnknownValueError: update_status("Tidak dapat mengenali suara.")
        except sr.RequestError: update_status("Layanan suara tidak tersedia.")
        except sr.WaitTimeoutError: update_status("Tidak ada suara terdeteksi.")
        finally:
            listen_button.config(state=tk.NORMAL)
            app.after(1500, update_status, "Siap menerima perintah...")

def start_listening_thread():
    threading.Thread(target=dengar_dan_proses, daemon=True).start()

def update_log(message):
    log_area.config(state=tk.NORMAL)
    log_area.insert(tk.END, message + "\n\n")
    log_area.config(state=tk.DISABLED)
    log_area.see(tk.END)

def update_status(message):
    status_bar.config(text=message)

app = tk.Tk()
app.title("Zestiii: Chimera")
app.geometry("700x550")
app.configure(bg="#1c1c1c")
app.resizable(False, False)

# ... (Sisa kode GUI sama persis dengan versi sebelumnya, salin dari kode lama Anda)
style = ttk.Style(app)
style.theme_use('clam')
style.configure("TButton", font=("Helvetica", 12), padding=10, background="#555", foreground="white")
style.map("TButton", background=[('active', '#777')])
style.configure("TFrame", background="#1c1c1c")
main_frame = ttk.Frame(app, padding="15")
main_frame.pack(fill=tk.BOTH, expand=True)
log_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=18, font=("Consolas", 11), bg="#2b2b2b", fg="#a9b7c6", relief=tk.FLAT, state=tk.DISABLED, bd=0, highlightthickness=0)
log_area.pack(pady=(0, 10), fill=tk.BOTH, expand=True)
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X)
listen_button = ttk.Button(button_frame, text="🎙️ Bicara", command=start_listening_thread)
listen_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
exit_button = ttk.Button(button_frame, text="Keluar", command=app.quit)
exit_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
status_bar = ttk.Label(main_frame, text="Siap menerima perintah...", font=("Helvetica", 10, "italic"), background="#1c1c1c", foreground="#00aaff", anchor=tk.W)
status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

if __name__ == "__main__":
    app.after(1000, lambda: bicara("Zestiii versi Chimera aktif. Siap untuk tugas kompleks.", display_log=False))
    app.mainloop()