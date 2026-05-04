"""
Kick → Telegram Yayın Bildirim Botu
GitHub Actions üzerinde çalışır.
State (yayın açık/kapalı) GitHub Variable olarak saklanır.
"""

import os
import requests

# ── Ayarlar (GitHub Secrets'tan gelir) ──────────────────────
BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
GROUP_ID    = os.environ["TELEGRAM_GROUP_ID"]
KICK_USER   = os.environ["KICK_USERNAME"]
GH_TOKEN    = os.environ["GH_TOKEN"]       # repo Variable okuma/yazma için
GH_REPO     = os.environ["GH_REPO"]        # örn: kullanici/repo-adi
# ────────────────────────────────────────────────────────────

KICK_URL = f"https://kick.com/api/v2/channels/{KICK_USER}"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

GH_VAR_URL = f"https://api.github.com/repos/{GH_REPO}/actions/variables/YAYIN_DURUMU"
GH_HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def onceki_durumu_oku() -> bool:
    """GitHub Variable'dan önceki yayın durumunu okur."""
    try:
        r = requests.get(GH_VAR_URL, headers=GH_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("value", "false").lower() == "true"
    except Exception as e:
        print(f"Variable okuma hatası: {e}")
    return False


def durumu_kaydet(canli: bool):
    """Mevcut yayın durumunu GitHub Variable'a yazar."""
    deger = "true" if canli else "false"
    try:
        # Önce var mı kontrol et
        r = requests.get(GH_VAR_URL, headers=GH_HEADERS, timeout=10)
        if r.status_code == 200:
            # Güncelle
            requests.patch(GH_VAR_URL, headers=GH_HEADERS,
                           json={"value": deger}, timeout=10)
        else:
            # Yeni oluştur
            url = f"https://api.github.com/repos/{GH_REPO}/actions/variables"
            requests.post(url, headers=GH_HEADERS,
                          json={"name": "YAYIN_DURUMU", "value": deger},
                          timeout=10)
    except Exception as e:
        print(f"Variable kaydetme hatası: {e}")


def kick_durumu_al() -> dict | None:
    """Kick API'den yayıncının canlı durumunu çeker."""
    try:
        r = requests.get(KICK_URL, headers=HEADERS, timeout=10)
        r.raise_for_status()
        veri = r.json()
        livestream = veri.get("livestream")
        if livestream:
            kategoriler = livestream.get("categories", [])
            kategori = kategoriler[0].get("name", "Bilinmiyor") if kategoriler else "Bilinmiyor"
            return {
                "canli": True,
                "baslik": livestream.get("session_title", "Başlık yok"),
                "kategori": kategori,
                "izleyici": livestream.get("viewer_count", 0),
                "url": f"https://kick.com/{KICK_USER}",
            }
        return {"canli": False}
    except Exception as e:
        print(f"Kick API hatası: {e}")
        return None


def telegram_gonder(mesaj: str):
    """Telegram grubuna mesaj gönderir."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": GROUP_ID,
            "text": mesaj,
            "parse_mode": "HTML",
        }, timeout=10)
        r.raise_for_status()
        print("✅ Telegram bildirimi gönderildi.")
    except Exception as e:
        print(f"❌ Telegram hatası: {e}")


def main():
    print(f"🔍 Kontrol ediliyor: kick.com/{KICK_USER}")

    durum = kick_durumu_al()
    if durum is None:
        print("⚠️ Kick API'ye ulaşılamadı, çıkılıyor.")
        return

    simdi_canli   = durum["canli"]
    onceki_canli  = onceki_durumu_oku()

    print(f"Önceki durum: {'🔴 Canlı' if onceki_canli else '⚫ Offline'}")
    print(f"Şimdiki durum: {'🔴 Canlı' if simdi_canli else '⚫ Offline'}")

    if simdi_canli and not onceki_canli:
        mesaj = (
            f"🔴 <b>{KICK_USER} YAYINA GİRDİ!</b>\n\n"
            f"🎮 <b>Kategori:</b> {durum['kategori']}\n"
            f"📺 <b>Başlık:</b> {durum['baslik']}\n"
            f"👥 <b>İzleyici:</b> {durum['izleyici']}\n\n"
            f"👉 <a href=\"{durum['url']}\">Yayına katıl!</a>"
        )
        telegram_gonder(mesaj)

    elif not simdi_canli and onceki_canli:
        telegram_gonder(
            f"⏹️ <b>{KICK_USER}</b> yayını kapattı. Görüşmek üzere! 👋"
        )
    else:
        print("Durum değişmedi, bildirim gönderilmedi.")

    durumu_kaydet(simdi_canli)


if __name__ == "__main__":
    main()

