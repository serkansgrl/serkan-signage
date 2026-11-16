# Serkan Signage — Türkçe

**Evde, iş yerinde veya bir tablette kendi sunucunuzda çalışan dijital bilgilendirme panosu.**

[English](README.md) · [Deutsch](README.de.md)

## Serkan Signage ne yapar?

Serkan Signage; **fotoğraf slaytı, haftalık yemek listesi, hava durumu, RSS haberleri ve günlük beş bilgi yarışması sorusunu** tek bir ekranda birleştiren açık kaynaklı bir Python/Docker uygulamasıdır. TV modunda haberlerle sorular otomatik sırayla gösterilir. Sorularda doğru cevap, ekran değişmeden kısa süre önce vurgulanır.

### Özellikler

- **Fotoğraflar:** yönetim panelinden fotoğraf yükle veya NAS klasörünü salt okunur bağla
- **Yemek listesi:** pazartesiden pazara günlük yemekleri düzenle
- **Hava durumu:** Open-Meteo üzerinden yedi günlük tahmin; şehir ve koordinatlar düzenlenebilir
- **Haberler:** varsayılan BR24 RSS, değiştirilebilir RSS ve güvenilir haber sitesi listesi
- **Günlük bilgi yarışması:** her gün beş adet Almanca çoktan seçmeli soru
- **TV modu:** haberler ve sorular otomatik değişir
- **Yönetim paneli:** `/serkan` adresinde şifreyle korunan alan
- **PWA:** desteklenen telefon ve tabletlerde uygulama gibi yükleme, tam ekran

**Not:** Belgeler Türkçe, Almanca ve İngilizcedir; uygulamanın mevcut arayüzü ve soru bankası ağırlıklı olarak **Almancadır**.

## Gerekenler

Docker Engine, Docker Compose eklentisi, boş bir port (varsayılan 8098). NAS fotoğrafları isteğe bağlıdır.

## Docker ile kurulum

```sh
git clone https://github.com/serkansgrl/serkan-signage.git
cd serkan-signage
cp .env.example .env
```

**Önemli:** `.env` dosyasındaki `INITIAL_ADMIN_PASSWORD` değerini en az 12 karakterlik, sana özel güçlü bir şifreyle değiştir.

```sh
docker compose up -d --build
docker compose ps
```

Docker'ın kurulu olduğu bilgisayarda `http://127.0.0.1:8098/` aç. Yönetim adresi: `http://127.0.0.1:8098/serkan`.

Varsayılan olarak **yalnızca localhost** üzerinden erişilebilir. Aynı yerel ağdaki başka cihazların ulaşmasını istiyorsan `.env` içine `BIND_ADDRESS=0.0.0.0` yaz ve güvenlik duvarıyla erişimi sınırla. İnternet erişiminde HTTPS reverse proxy kullan, `COOKIE_SECURE=true` ayarla ve yönetici paneli için ikinci bir erişim koruması ekle.

`INITIAL_ADMIN_PASSWORD` yalnızca boş veri alanına **ilk kurulumda** uygulanır. Sonradan `.env` değiştirmek mevcut şifreyi sıfırlamaz; yönetici panelinden değiştirilebilir.

## Fotoğraf ve NAS bağlantısı

Yüklenen fotoğraflar, ayarlar, parola özeti ve oturum anahtarı `signage_data` adlı kalıcı Docker volume içinde tutulur. Bu verileri yedekle; GitHub'a yükleme.

NAS klasörünü önce Docker host üzerinde SMB3 veya NFS ile bağla. Sonra `.env` dosyasında `NAS_PHOTOS_PATH` değişkenine bu **sunucu klasörünün yolunu** yaz. Docker konteyneri NAS fotoğraflarını salt okunur görür. NAS kullanıcı adı ve şifresi uygulama koduna girilmez.

JPEG, PNG, GIF ve WebP fotoğrafları desteklenir.

## Ayarlar

| Değişken | Açıklama |
| --- | --- |
| `INITIAL_ADMIN_PASSWORD` | İlk yönetim şifresi, en az 12 karakter |
| `BIND_ADDRESS` | Sunucunun dinleme adresi (varsayılan `127.0.0.1`) |
| `HTTP_PORT` | Dış port (varsayılan `8098`) |
| `COOKIE_SECURE` | HTTPS için `true` |
| `FRAME_ANCESTORS` | Ana ekranın iframe içinde açılabileceği güvenilir adresler |
| `NAS_PHOTOS_PATH` | NAS fotoğraflarının host klasörü |
| `NEWS_FEEDS` | Virgülle ayrılan RSS kaynakları |
| `NEWS_ALLOWED_HOSTS` | Haber bağlantıları için izin verilen alan adları |
| `NEWS_SOURCE_LABEL` | Haber kaynağının görünen adı |
| `TZ` | Saat dilimi, varsayılan `Europe/Berlin` |

**Güvenlik:** Ekran görüntüsü, fotoğraflar ve `/api/state`, `/api/extras` adresleri kimlik doğrulaması gerektirmez. Sadece yönetim işlemleri şifrelidir. Kişisel fotoğraflar içeren bir kurulumu doğrudan internete açma.

## Test ve güncelleme

```sh
python3 -m unittest discover -s tests -v
docker compose config
docker compose up -d --build
```

Ek belgeler: [Güvenlik](SECURITY.md) · [Geçiş](MIGRATION.md) · [MIT Lisansı](LICENSE). Üçüncü taraf haber ve görseller kendi yayıncılarının haklarına tabidir.
