# Serkan Signage — Türkçe

**Ev, ofis ve ortak ekranlar için kendi sunucunuzda çalışan dijital bilgilendirme panosu.**

> **Durum: Yayına hazırlık.** Gerçek uygulama kaynak kodu henüz güvenlik incelemesinden geçmediği için bu depoya eklenmedi. Şimdiki dosyalar Docker ve belgelendirme altyapısıdır; **henüz kurulup çalıştırılabilen tamamlanmış sürüm değildir**.

## Mevcut özel kurulumun özellikleri
- **Fotoğraflar:** klasördeki fotoğrafları otomatik sırayla gösterir; NAS klasörleri sunucuya bağlanabilir.
- **Yemek planı:** günlük/haftalık menü veya yemek bilgilerini gösterir ve yönetir.
- **Hava durumu:** Open-Meteo verilerini kullanır.
- **Haberler:** RSS kaynaklarından haber gösterir; mevcut kurulum BR24 kaynaklarını kullanır.
- **Günlük bilgi yarışması:** beş soru ve cevapların otomatik gösterimi.
- **TV modu:** ekran içeriğini otomatik değiştirir.
- **Yönetim paneli:** şifreyle korunan düzenleme ekranı.
- **PWA:** desteklenen cihazlarda web uygulaması olarak kurulabilir.

## Nasıl çalışır?
Hafif bir Python web sunucusu panoyu ve yönetim ekranını sunar. Docker üzerinden çalıştırılır; fotoğraflar, yapılandırma ve güvenlik anahtarları uygulama kodundan ayrı saklanmalıdır. İnternetten erişimde HTTPS ve ek yönetim paneli erişim koruması önerilir.

## Planlanan Docker kurulumu
```bash
cp .env.example .env
docker compose up -d --build
```
**Henüz çalışmaz:** Güvenlik kontrolünden geçen gerçek `app.py` kodunun ve kalıcı veri bağlarının eklenmesi gerekir.

## GitHub'da ne paylaşılmayacak?
Kişisel fotoğraflar, NAS şifreleri, gerçek IP/alan adı yapılandırmaları, uygulama secret dosyası ve canlı sunucunun kişisel verileri.

Diğer belgeler: [English](README.md) · [Deutsch](README.de.md) · [Güvenlik](SECURITY.md).
