import time 
import threading 

#Digunakan untuk mengecek tampilan di laptop
#Jadi tidak akan membuat vscode error 

try: 
    import RPi.GPIO as GPIO 
    GPIO_AVAILABLE = True
    print("Pin is Available to use")
except: 
    GPIO_AVAILABLE = False 
    print("Pin is not available")

if GPIO_AVAILABLE: 
    #Menggunakan pin BCM 
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    #Pemetaan pin yang digunakan untuk Magnet Lock 
    pin_magnet = {
        1: 16,      
        2: 25,
        3: 24,
        4: 22
    }

    pin_buzzer = {
        1: 27
    }
    
    for pin in  pin_magnet.values():
    #pin dimatikan dulu untuk menjaga sisa listrik yang ada 
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)

    for pin in pin_buzzer.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

else:
    pin_magnet = {
        1: 22,
        2: 23,
        3: 24,
        4: 25
    }
    pin_buzzer = {
        1: 17
    }

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

# Fungsi membuka laci 
def membuka_laci(nomor_laci):
    pin_target = pin_magnet.get(nomor_laci)

    if pin_target:
        print(f"membuka laci {nomor_laci}, pin BCM {pin_target}")

        if GPIO_AVAILABLE: 
            GPIO.output(pin_target, GPIO.LOW) #laci terbuka 

        time.sleep(5) #terbuka selama 5 detik 

        print(f"Mengunci kembali laci {nomor_laci}")

        if GPIO_AVAILABLE:
            GPIO.output(pin_target, GPIO.HIGH)

#Fungsi pemicu yang akan dipanggil 

def buka_laci_otomatis(nomor_laci):
    #Membuka laci agar UI tetap lancar 
    task = threading.Thread(target=membuka_laci, args=(nomor_laci,))
    task.start()

def bersihkan_gpio():
    #memanggil ketika aplikasi di tutup 
    if GPIO_AVAILABLE:
        GPIO.cleanup()
