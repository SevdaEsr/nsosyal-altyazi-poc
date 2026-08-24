# Gerekli standart Python modüllerini içe aktarıyoruz
import os  # Dosya ve dizin yolları işlemleri için
import subprocess  # FFmpeg'i alt süreç olarak çalıştırabilmek için
import sys  # Sistem argümanları ve çalışma durumu kontrolleri için

def check_ffmpeg():
    """Sistemde FFmpeg aracının kurulu olup olmadığını kontrol eder."""
    try:
        # ffmpeg -version komutunu çalıştırıp çıktıyı sessize alıyoruz
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True  # FFmpeg bulunursa True dönüyoruz
    except (FileNotFoundError, subprocess.CalledProcessError):
        # FFmpeg bulunamazsa hata mesajı verip False dönüyoruz
        print("[HATA] Sistemde FFmpeg bulunamadı! Lütfen FFmpeg'in yüklü ve PATH'e ekli olduğundan emin olun.")
        return False

def extract_audio_from_video(video_path: str, output_audio_path: str) -> bool:
    """FFmpeg kullanarak videodan 16kHz, mono, PCM 16-bit formatında ses ayıklar."""
    print(f"[İŞLEM] Videodan ses kanalı ayıklanıyor: {video_path}")
    
    # FFmpeg komutunu bir liste halinde oluşturuyoruz
    ffmpeg_command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_audio_path
    ]
    
    try:
        # FFmpeg komutunu çalıştırıyoruz ve çıktıları terminalde gizliyoruz
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[BAŞARILI] Ses ayıklandı ve kaydedildi: {output_audio_path}")
        return True
    except subprocess.CalledProcessError as e:
        # FFmpeg çalışırken hata oluşursa yakalayıp ekrana basıyoruz
        print(f"[HATA] FFmpeg ses ayıklama işlemi başarısız oldu: {e}")
        return False

def format_timestamp(seconds: float, is_vtt: bool = False) -> str:
    """Saniyeyi altyazı formatına uygun zamana (HH:MM:SS,mmm veya HH:MM:SS.mmm) dönüştürür."""
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    
    if milliseconds >= 1000:
        seconds += 1
        milliseconds -= 1000
        
    minutes, seconds_int = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    millisecond_separator = "." if is_vtt else ","
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}{millisecond_separator}{milliseconds:03d}"

def write_srt_file(segments: list, output_path: str):
    """Zaman damgalı segmentleri standart SRT altyazı dosyası olarak yazar."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, segment in enumerate(segments, 1):
            start_time = format_timestamp(segment['start'], is_vtt=False)
            end_time = format_timestamp(segment['end'], is_vtt=False)
            text = segment['text'].strip()
            f.write(f"{idx}\n{start_time} --> {end_time}\n{text}\n\n")
    print(f"[KAYDEDİLDİ] SRT dosyası oluşturuldu: {output_path}")

def write_vtt_file(segments: list, output_path: str):
    """Zaman damgalı segmentleri standart WebVTT altyazı dosyası olarak yazar."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for idx, segment in enumerate(segments, 1):
            start_time = format_timestamp(segment['start'], is_vtt=True)
            end_time = format_timestamp(segment['end'], is_vtt=True)
            text = segment['text'].strip()
            f.write(f"{idx}\n{start_time} --> {end_time}\n{text}\n\n")
    print(f"[KAYDEDİLDİ] WebVTT dosyası oluşturuldu: {output_path}")

def run_stt_pipeline(video_path: str, model_size: str = "turbo"):
    """Tüm ses ayıklama, Whisper ile deşifre etme ve altyazı yazma adımlarını koordine eder."""
    if not check_ffmpeg():
        sys.exit(1)
        
    if not os.path.exists(video_path):
        print(f"[HATA] Belirtilen video dosyası bulunamadı: {video_path}")
        sys.exit(1)
        
    base_name = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_name}_temp.wav"
    
    if not extract_audio_from_video(video_path, temp_audio_path):
        sys.exit(1)
        
    try:
        print("[İŞLEM] openai-whisper kütüphanesi yükleniyor...")
        import whisper
        
        # Whisper model boyutunu varsayılan olarak turbo yükletiyoruz
        print(f"[İŞLEM] Whisper '{model_size}' modeli belleğe yükleniyor...")
        model = whisper.load_model(model_size)
        
        print("[İŞLEM] Ses dosyasının deşifresi (Speech-to-Text) başlatıldı...")
        result = model.transcribe(temp_audio_path, language="tr")
        
        srt_output = f"{base_name}.srt"
        vtt_output = f"{base_name}.vtt"
        
        write_srt_file(result['segments'], srt_output)
        write_vtt_file(result['segments'], vtt_output)
        
        print("\n=== DEŞİFRE İŞLEMİ BAŞARIYLA TAMAMLANDI ===")
        print(f"Orijinal Video: {video_path}")
        print(f"Geçici Ses: {temp_audio_path}")
        print(f"SRT Çıktısı: {srt_output}")
        print(f"WebVTT Çıktısı: {vtt_output}")
        print("===========================================")
        
    except ImportError:
        print("[HATA] 'openai-whisper' kütüphanesi kurulu değil.")
    except Exception as e:
        print(f"[SİSTEM HATASI] İşlem sırasında bir hata meydana geldi: {e}")
    finally:
        if os.path.exists(temp_audio_path):
            print("[TEMİZLİK] Geçici ses dosyası (.wav) diskten temizleniyor...")
            os.remove(temp_audio_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python nsosyal_poc_stt.py <video_dosyasi_yolu> [model_boyutu]")
        sys.exit(1)
        
    video_input = sys.argv[1]
    # Varsayılan model argümanını turbo olarak belirliyoruz
    model_input = sys.argv[2] if len(sys.argv) > 2 else "turbo"
    
    run_stt_pipeline(video_input, model_input)
