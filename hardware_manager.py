import time 
import threading 

# Digunakan untuk mengecek tampilan di laptop
# Jadi tidak akan membuat vscode error 

try: 
    import RPi.GPIO as GPIO 
    GPIO_AVAILABLE = True
    print("Pin is Available to use")
except: 
    GPIO_AVAILABLE = False 
    print("Pin is not available")

if GPIO_AVAILABLE: 
    # Menggunakan pin urutan fisik jarum (BOARD)
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Pemetaan pin yang digunakan untuk Magnet Lock 
    pin_magnet = {
        1: 16,      
        2: 25,
        3: 24,
        4: 22
    }

    pin_buzzer = {
        1: 27
    }
    
    PIN_LED_MERAH = 26 
    PIN_LED_HIJAU = 23 
    
    # Setup Magnet
    for pin in pin_magnet.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH) # Magnet ON (Terkunci)

    # Setup Buzzer
    for pin in pin_buzzer.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    # 🔥 2. SETUP KONDISI AWAL (Standby: Laci Terkunci = Merah Nyala)
    GPIO.setup(PIN_LED_MERAH, GPIO.OUT)
    GPIO.output(PIN_LED_MERAH, GPIO.HIGH)

    GPIO.setup(PIN_LED_HIJAU, GPIO.OUT)
    GPIO.output(PIN_LED_HIJAU, GPIO.LOW)

else:
    pin_magnet = {1: 22, 2: 23, 3: 24, 4: 25}
    pin_buzzer = {1: 17}
    PIN_LED_MERAH = 99
    PIN_LED_HIJAU = 100

def bunyikan_buzzer_error(durasi=1.5):
    def _bunyi():
        target_pin = pin_buzzer.get(1)
        print(f"🚨 BUZZER MENYALA di PIN {target_pin} selama {durasi} detik!")
        if GPIO_AVAILABLE:
            GPIO.output(target_pin, GPIO.HIGH)
            time.sleep(durasi)
            GPIO.output(target_pin, GPIO.LOW)
        else:
            time.sleep(durasi)
            print("🚨 BUZZER MATI (Simulasi)")
            
    threading.Thread(target=_bunyi, daemon=True).start()

buzzer_lockdown_aktif = False

def buzzer_on():
    global buzzer_lockdown_aktif
    if buzzer_lockdown_aktif:
        return
    buzzer_lockdown_aktif = True
    target_pin = pin_buzzer.get(1)

    def beep_loop():
        if not GPIO_AVAILABLE:
            print("buzzer on (simulasi)")

        while buzzer_lockdown_aktif: 
            if GPIO_AVAILABLE:
                GPIO.output(target_pin, GPIO.HIGH)
            time.sleep(0.5)

            if GPIO_AVAILABLE:
                GPIO.output(target_pin, GPIO.LOW)
            time.sleep(0.5)
    
    threading.Thread(target=beep_loop, daemon=True).start()

def buzzer_off():
    global buzzer_lockdown_aktif 
    buzzer_lockdown_aktif = False
    target_pin = pin_buzzer.get(1)
    if GPIO_AVAILABLE:
        GPIO.output(target_pin, GPIO.LOW)
    else:
        print("BUZZER OFF")

# 🔥 3. LOGIKA BUKA LACI ANTI-CRASH
def membuka_laci(nomor_laci):
    try:
        pin_target = pin_magnet.get(nomor_laci)

        if pin_target:
            print(f"Membuka laci {nomor_laci}, pin BOARD {pin_target}")

            if GPIO_AVAILABLE: 
                GPIO.output(pin_target, GPIO.LOW) # Magnet terlepas (Laci terbuka)
                
                # LACI TERBUKA: Hijau Nyala (Aman Ditarik), Merah Mati
                GPIO.output(PIN_LED_MERAH, GPIO.LOW)
                GPIO.output(PIN_LED_HIJAU, GPIO.HIGH)

            # Istirahat 5 detik
            time.sleep(5) 

            print(f"Mengunci kembali laci {nomor_laci}")

            if GPIO_AVAILABLE:
                GPIO.output(pin_target, GPIO.HIGH) # Magnet kembali mengunci
                
                # KEMBALI STANDBY: Merah Nyala (Terkunci), Hijau Mati
                GPIO.output(PIN_LED_MERAH, GPIO.HIGH)
                GPIO.output(PIN_LED_HIJAU, GPIO.LOW)
                
    except Exception as e:
        # 🔥 Jika ada pin salah atau korslet, terminal akan berteriak di sini!
        print(f"❌ ERROR FATAL DI THREAD LACI: {e}")

# Fungsi pemicu yang akan dipanggil 
def buka_laci_otomatis(nomor_laci):
    # Membuka laci agar UI tetap lancar 
    task = threading.Thread(target=membuka_laci, args=(nomor_laci,))
    task.start()

def bersihkan_gpio():
    # memanggil ketika aplikasi di tutup 
    if GPIO_AVAILABLE:
        GPIO.cleanup()