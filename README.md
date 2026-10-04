# kindle-dash 📜

Eski, jailbreak'li bir Kindle'ı **nostaljik bir takvim yaprağına / bilgi ekranına** çeviren küçük bir proje. Sunucu gerekmez: ekran görüntüsünü GitHub Actions üretir, GitHub Pages yayınlar, Kindle günde birkaç kez uyanıp indirir ve tekrar uykuya geçer.

> **English summary:** Turns a jailbroken Kindle into a low-power info screen styled as a vintage Turkish tear-off calendar leaf. A GitHub Actions workflow renders a grayscale PNG every hour (weather, sunrise/sunset, BTC, USD/EUR from the Turkish central bank, a daily quote) and publishes it to GitHub Pages. A small KUAL extension on the Kindle wakes up via the RTC alarm at set hours, downloads the PNG matching its screen size, shows it, turns Wi-Fi off and suspends again. No server needed. UI text is in Turkish.

| Takvim yaprağı (varsayılan) | Modern panel |
|:---:|:---:|
| ![Takvim yaprağı teması](docs/takvim.png) | ![Modern tema](docs/modern.png) |

*Görsellerdeki hava ve piyasa rakamları örnek veridir.*

---

## İçindekiler
- [Ne gösteriyor](#ne-gösteriyor)
- [Nasıl çalışıyor](#nasıl-çalışıyor)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Ayarlar](#ayarlar)
- [Kullanım](#kullanım)
- [Sorun giderme](#sorun-giderme)
- [Bilinen kısıtlar](#bilinen-kısıtlar)
- [Veri kaynakları](#veri-kaynakları)

---

## Ne gösteriyor

**Takvim yaprağı teması**
- Ay, iri gün rakamı ve gün adı (eski duvar takvimi düzeninde)
- Yıl, hafta numarası, yılın kaçıncı günü
- Güneşin doğuş / batış saati, gündüz ve gece süresi
- Seçtiğin şehir için anlık hava, günün en düşük / en yüksek sıcaklığı, yağış ihtimali
- BTC (USD), USD/TRY ve EUR/TRY + günlük değişim
- Günün sözü: atasözleri, ünlü sözler ve kısa "sabah notları" (50 adet, her gün biri)

**Modern tema**
- Tarih, anlık hava + 3 günlük tahmin
- BTC, USD/TRY, EUR/TRY için **son 14 günün** küçük çizgi grafikleri
- Günün sözü

**Kindle'ın kendi yazdığı durum satırı** (sol üst köşe)
- `Pil 87  Guncellendi 08:00` → pil yüzdesi ve son başarılı güncelleme saati
- İndirme başarısız olursa sonuna `(ESKI)`, pil %15'in altına düşerse `SARJ ET` eklenir

---

## Nasıl çalışıyor

```
GitHub Actions (her saat :13'te)
   └─ generator/render.py → hava + kur + BTC verisini çeker, PNG çizer
        └─ 4 boyutta çıktı: dashboard.png, dashboard_600x800.png,
           dashboard_758x1024.png, dashboard_1072x1448.png
   └─ GitHub Pages'e yayınlar → https://KULLANICI.github.io/kindle-dash/

Kindle (06:00–22:00 arası 2 saatte bir)
   └─ RTC alarmıyla uyanır → Wi-Fi açar → saati düzeltir
   └─ Ekran çözünürlüğünü okur → kendine uygun PNG'yi indirir
   └─ Ekrana basar + durum satırını yazar → Wi-Fi kapatır → derin uyku
```

**Neden saatlik render, Kindle neden 2 saatte bir?** GitHub zamanlanmış workflow'ları saatlerce geciktirebiliyor ya da atlayabiliyor. Saatlik üretim, Kindle hangi saatte uyanırsa uyansın elinde en fazla 1–2 saatlik bir görüntü olmasını sağlıyor.

---

## Gereksinimler

- **Jailbreak'li bir Kindle** + **KUAL** (Kindle Unified Application Launcher)
  - Jailbreak bu reponun konusu değil. Güncel ve güvenilir kaynak: **[kindlemodding.org](https://kindlemodding.org/)**
  - Firmware'ine uygun yöntemi oradan seç (bu proje FW 5.10.2'de WinterBreak ile kurulmuş bir cihazda geliştirildi)
- Kindle'ın kayıtlı olduğu bir **Wi-Fi** ağı
- Bir **GitHub hesabı** (public repo'da Actions ve Pages ücretsiz)
- Ekstra Kindle eklentisi **gerekmez**: SSH/USBNetwork kurmana gerek yok, dosyalar USB ile kopyalanıyor

⚠️ **Sorumluluk reddi:** Jailbreak cihazın garantisini etkileyebilir ve yanlış uygulanırsa cihazı kullanılamaz hâle getirebilir. Risk sana ait.

---

## Kurulum

### 1. Repoyu kendine kopyala
- Sağ üstten **Fork** et (repo **public** kalmalı, ücretsiz Pages için gerekli)

### 2. Şehrini ayarla
`.github/workflows/render.yml` içindeki **Render PNG** adımına `env:` ekle:

```yaml
      - name: Render PNG
        env:
          DASH_CITY: "Gebze"
          DASH_LAT: "40.802"
          DASH_LON: "29.430"
          DASH_THEME: "takvim"   # veya "modern"
        run: |
          mkdir -p site
          python generator/render.py --out site/dashboard.png
          cp site/dashboard.png site/index.png
```

Enlem/boylamı Google Haritalar'da şehrine sağ tıklayıp öğrenebilirsin. Hiçbir şey yazmazsan varsayılan Gebze'dir.

### 3. GitHub Pages'i aç
- Repo → **Settings → Pages → Source: GitHub Actions**

### 4. İlk görüntüyü üret
- **Actions → Render dashboard → Run workflow**
- Yeşil tik gelince tarayıcıda aç:
  `https://KULLANICI.github.io/kindle-dash/dashboard_600x800.png`

### 5. Kindle tarafını hazırla
1. `kindle/dash.conf` içindeki adresi kendi kullanıcı adınla değiştir:
   ```sh
   DASH_URL="https://KULLANICI.github.io/kindle-dash/dashboard.png"
   ```
2. Kindle'ı USB ile bağla, `kindle/` klasöründeki **4 dosyayı** Kindle'da şu klasöre kopyala:
   ```
   extensions/kindle-dash/
     ├─ config.xml
     ├─ menu.json
     ├─ dash.conf
     └─ dash.sh
   ```
   Windows'ta Not Defteri ile düzenleyebilirsin, satır sonu (CRLF) farkını script ilk çalışmada kendisi düzeltiyor.
3. Kindle'ı bilgisayardan güvenli çıkar

### 6. Dene
- **KUAL → Kindle Dash → "1) Test"** → ~1 dk içinde görüntü ekrana gelmeli
- Sorunsuzsa **"2) Dashboard'u başlat"**

---

## Ayarlar

### Render tarafı (workflow `env:`)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DASH_CITY` | `Gebze` | Ekranda yazan şehir adı |
| `DASH_LAT` / `DASH_LON` | `40.802` / `29.430` | Hava durumu ve güneş saatleri için konum |
| `DASH_THEME` | `takvim` | `takvim` ya da `modern` |

Saat dilimi `Europe/Istanbul` olarak sabit, değiştirmek için `generator/render.py` içindeki `TZ`'yi düzenle.

### Kindle tarafı (`kindle/dash.conf`)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DASH_URL` | — | Yayınlanan PNG'nin adresi (`_600x800` gibi ekleri script kendisi ekler) |
| `REFRESH_HOURS` | `"6 8 10 12 14 16 18 20 22"` | Kindle'ın uyanıp yenileyeceği saatler (yerel saat, tam saat) |
| `UTC_OFFSET_SEC` | `10800` | Yerel saatin UTC farkı, saniye (Türkiye: +3 saat) |

Daha az yenileme = daha uzun pil. Örneğin `REFRESH_HOURS="6 17"` günde sadece iki kez yeniler.

### Günün sözü
`generator/quotes.json` dosyasını düzenle:
```json
{"text": "Damlaya damlaya göl olur."},
{"text": "Ruh, düşüncelerinin rengine boyanır.", "author": "Marcus Aurelius"}
```
`author` boş bırakılırsa ekranda yazar satırı çıkmaz. Aynı söz gün boyunca ekranda kalır, ertesi gün değişir. Yabancı sözler serbest Türkçe çeviridir.

---

## Kullanım

| İstediğin | Yapacağın |
|---|---|
| Tek seferlik deneme (Kindle arayüzü açık kalır) | KUAL → Kindle Dash → **1) Test** |
| Bilgi ekranı modunu başlat | KUAL → Kindle Dash → **2) Dashboard'u başlat** |
| Normal Kindle'a dön | Güç tuşunu **~40 sn** basılı tut → yeniden başlar |
| Ayar / script değiştir | Önce normal Kindle'a dön, sonra USB ile dosyayı düzenle |
| Yayınlanan görüntüyü gör | `https://KULLANICI.github.io/kindle-dash/dashboard_600x800.png` |

Bilgi ekranı modunda Kindle arayüzü durdurulur. Wi-Fi sadece yenileme sırasında ~1 dk açılır, sonra kapatılır (Kindle bunu uçak modu olarak gösterir). Bu hem pil hem de istenmeyen firmware güncellemelerine karşı koruma içindir.

---

## Sorun giderme

Her şey Kindle'da `extensions/kindle-dash/dash.log` dosyasına yazılır. USB ile bağlayıp aç:

| Log'da gördüğün | Anlamı |
|---|---|
| `screen=600x800 url=...` | Ekran boyutu doğru algılandı, hangi PNG'nin istendiği |
| `fetched ok` | İndirme başarılı |
| `wifi: not connected` | Wi-Fi'ye bağlanamadı → ağın Kindle'da kayıtlı mı? |
| `fetch FAILED, keeping old image` | Adres yanlış ya da Pages henüz yayınlamamış |
| `time set: ...` | Saat, sunucunun cevabından düzeltildi |
| `suspend 7200s via /sys/class/rtc/rtc1` | Bir sonraki yenilemeye kadar uykuya geçti |
| `shown: Pil 87  Guncellendi 08:00` | Durum satırına yazılan metin |

**Görüntü ekrana sığmıyor / taşıyor** → Log'da `screen=` satırına bak. Ekranın listede yoksa (`600x800`, `758x1024`, `1072x1448`) `generator/render.py` içindeki `SIZES` listesine ekle.

**"Başlat" sonrası ekran beyaz kaldı** → Güç tuşu ~40 sn, Kindle normale döner. Log'da `gui stopped` satırından sonra ne yazdığına bak.

**Ekran saatlerce güncellenmiyor** → Önce Actions sekmesinde son çalışmanın saatine bak. GitHub zamanlamaları gecikebilir, sorun Kindle'da olmayabilir.

---

## Bilinen kısıtlar

- **Test edilen cihaz tek:** 600×800, 167 dpi, firmware 5.10.2. Diğer modellerde çalışması beklenir ama denenmedi. Farklı bir cihazda denersen sonucu paylaşırsan sevinirim
- **GitHub zamanlaması kesin değil:** Zamanlanmış workflow'lar dakikalar ile saatler arası gecikebilir
- **60 gün kuralı:** Hiç commit almayan public repolarda GitHub zamanlanmış workflow'ları **60 gün sonra otomatik durdurur**. Durdurmadan önce e-posta atar, tek tıkla yeniden açılır
- **Kur verisi:** TCMB her iş günü ~15:30'da yayınlar. Sabah ekranında önceki iş gününün kuru görünür, hafta sonu kur değişmez
- **Durum satırı Türkçe karakter basamaz:** Kindle'ın yerleşik yazı tipi yüzünden "Guncellendi", "SARJ ET" gibi yazılır
- **`%` işareti:** Kindle'ın `eips` aracı `%`'yi biçim komutu sanıyor, durum satırına eklenmemeli
- **Saat dilimi:** Kindle'ın kendi saat dilimi ayarı kullanılmaz; hesaplar UTC + `UTC_OFFSET_SEC` ile yapılır. Yaz saati uygulayan bir ülkedeysen bu değeri dönemsel olarak güncellemen gerekir

---

## Veri kaynakları

Hepsi ücretsiz ve API anahtarı istemiyor.

| Veri | Kaynak |
|---|---|
| Hava durumu, gün doğumu/batımı | [Open-Meteo](https://open-meteo.com/) |
| BTC fiyatı ve 14 günlük geçmiş | [CoinGecko](https://www.coingecko.com/) |
| USD/TRY, EUR/TRY (Döviz Satış) | [TCMB gösterge niteliğindeki kurlar](https://www.tcmb.gov.tr/kurlar/today.xml) |

Bir kaynak yanıt vermezse o bölüm boş kalır, ekranın geri kalanı yine çizilir.

---

## Repo yapısı

```
.github/workflows/render.yml   # saatlik render + GitHub Pages yayını
generator/
  render.py                    # veri çekme, modern tema, çoklu boyut çıktı
  takvim.py                    # takvim yaprağı teması
  quotes.json                  # günün sözleri
kindle/                        # Kindle'a kopyalanacak KUAL eklentisi
  config.xml, menu.json        # KUAL menüsü
  dash.conf                    # ayarlar
  dash.sh                      # uyan → indir → göster → uyu döngüsü
docs/                          # README görselleri
```

**Yerelde önizleme** (Python 3 + Pillow, DejaVu fontları):
```sh
cd generator
python render.py --mock --out preview.png                  # örnek veriyle
DASH_THEME=modern python render.py --out preview.png       # gerçek veriyle
DASH_NOW=2026-11-30T06:00 python render.py --mock --out p.png   # başka bir tarihi dene
```

---

## Teşekkür

- Kindle jailbreak ve eklenti topluluğuna, özellikle [kindlemodding.org](https://kindlemodding.org/) ve KUAL geliştiricilerine
- Tasarım, Türkiye'deki eski koparmalı duvar takvimlerinden esinlenmiştir
