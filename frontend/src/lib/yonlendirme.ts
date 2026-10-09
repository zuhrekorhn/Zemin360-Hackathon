/**
 * Girişe ve role göre yönlendirme kuralları (docs/kimlik-ve-dongu.md § 7).
 * Saf fonksiyonlar; testleri yonlendirme.test.ts'de.
 */

import type { Rol, YetenekKartiOzeti } from "@/lib/api";

/** Her rolün paneli: giriş sonrası ve rolü uymayan sayfadan buraya gidilir. */
export function panelYolu(rol: Rol): string {
  if (rol === "genc") return "/genc";
  if (rol === "kurum") return "/kurum";
  return "/girvak";
}

/**
 * Gencin "Kartım"ı (G17: gencin tek kartı var). Kartı varsa kart
 * sayfası, yoksa kartı oluşturduğu Keşif sohbeti.
 */
export function kartYolu(kart: Pick<YetenekKartiOzeti, "id"> | null): string {
  return kart ? `/kart/${kart.id}` : "/kesif";
}

const GIRIS_SAYFALARI = ["/giris", "/kayit"];

/** Canlılık'ın iş birliğine bağlı hatırlatmaları: iş birliği sayfasına. */
const CANLILIK_ISBIRLIGI = new Set([
  "plan_onaysiz",
  "isbirligi_hareketsiz",
  "adim_gecikti",
]);

/** Takip Ajanı'nın bildirim türleri (backend app/models/bildirim.py). */
const TAKIP_TURLERI = new Set([
  "plan_onerildi",
  "plan_duzenlendi",
  "plan_onayi",
  "plan_onaylandi",
  "adim_isaretlendi",
  "adim_tamamlandi",
  "isbirligi_tamamlandi",
]);

/**
 * `?sonra=` güvenli mi? Yalnızca bu sitenin içindeki bir yol kabul edilir:
 * `//baska.site`, `/\baska.site` ya da `https://…` ile açık yönlendirme
 * yapılmasın. Giriş/kayıt sayfasına geri dönmek de anlamsız (döngü).
 */
export function guvenliSonra(sonra: string | null): string | null {
  if (!sonra || !sonra.startsWith("/")) return null;
  if (sonra.startsWith("//") || sonra.startsWith("/\\")) return null;
  const yol = sonra.split(/[?#]/)[0];
  if (GIRIS_SAYFALARI.includes(yol)) return null;
  return sonra;
}

/** Girişten sonra nereye: güvenli bir `sonra` varsa oraya, yoksa panele. */
export function giristenSonra(rol: Rol, sonra: string | null): string {
  return guvenliSonra(sonra) ?? panelYolu(rol);
}

/**
 * Yeni hesabın sahibi olmadığı kaynak sayfaları: kayıtlı başka bir hesabın
 * oturumundan kalan `sonra` (ör. çıkış yapılan gencin kart adresi) yeni
 * hesabı başkasının kartına, yani "bulunamadı"ya götürüyordu.
 */
const KAYITTA_SAYILMAYAN_YOLLAR = ["/kart/", "/isbirligi/", "/kurum/ilan/"];

/**
 * Kayıttan sonra nereye (docs/agent-specs.md § 1): genç doğrudan Keşif
 * sohbetine (onboarding; "Şimdilik atla" oradan panele), diğerleri panele.
 * Güvenli bir `sonra` varsa o öncelikli; yalnızca yeni hesabın sahibi
 * olamayacağı kaynak sayfaları (kart, iş birliği, ilan) yok sayılır.
 */
export function kayittanSonra(rol: Rol, sonra: string | null): string {
  const hedef = guvenliSonra(sonra);
  if (hedef && !KAYITTA_SAYILMAYAN_YOLLAR.some((o) => hedef.startsWith(o))) {
    return hedef;
  }
  return rol === "genc" ? "/kesif?ilk=1" : panelYolu(rol);
}

/**
 * Bildirime tıklayınca nereye (docs/kimlik-ve-dongu.md § 6).
 * Gence gidenler ana sayfanın ilgili bölümüne (yanıt bekleyen ilgi
 * "Seni bekleyenler"e, sonuçlanan ilişki "Süreçlerin"e); çalışmayla ilgili
 * olanlar (referans yanıtı, GİRVAK incelemesi) kart sayfasına. Kuruma
 * gidenler (yeni öneri, red) kurum paneline. İş birliği olan bildirim (kabul
 * ve Takip'in bütün türleri) doğrudan iş birliği sayfasına. Bilinmeyen tür
 * bildirim sayfasında kalır.
 */
export function bildirimHedefi(
  tur: string,
  isbirligiId: string | null = null,
  rol: Rol | null = null,
  kart: Pick<YetenekKartiOzeti, "id"> | null = null,
): string {
  if (
    isbirligiId &&
    (tur === "kabul" ||
      tur === "karsilikli_ilgi" ||
      TAKIP_TURLERI.has(tur) ||
      CANLILIK_ISBIRLIGI.has(tur))
  ) {
    return `/isbirligi/${isbirligiId}`;
  }
  // Firmalar arası ilgi (docs/kararlar.md F9): aday firmaya giden
  // ilgi bildirimleri gencin değil firmanın panelindeki bölümlere.
  if (rol === "kurum") {
    if (tur === "ilgi") return "/kurum#gelen-ilgiler";
    if (tur === "karsilikli_ilgi" || tur === "firsat_kapandi")
      return "/kurum#ilgilerimiz";
  }
  switch (tur) {
    // Canlılık. Yanıtsız ilginin son hatırlatması iki tarafa aynı
    // türle gider: genç ilgiler bölümüne, kurum önerilerine.
    case "oneri_bekliyor":
      return "/kurum#ihtiyaclar";
    case "ilgi_yanitsiz_1":
      return "/genc#bekleyenler";
    case "ilgi_yanitsiz_2":
      return rol === "kurum" ? "/kurum#oneriler" : "/genc#bekleyenler";
    case "yeni_firsat":
      return "/genc#firsatlar";
    // Gençten ilgi (docs/api-contracts.md)
    case "genc_ilgi":
    case "genc_ilgisi_yanitsiz":
      return "/kurum#ihtiyaclar";
    case "karsilikli_ilgi":
    case "firsat_kapandi":
      return "/genc#surecler";
    case "ilgi":
      return "/genc#bekleyenler";
    case "referans_yaniti":
    case "referans_yanit_yok":
      return kart ? kartYolu(kart) : "/genc";
    case "yeni_oneri":
      return "/kurum#ihtiyaclar";
    case "kabul":
      return "/kurum#isbirlikleri";
    case "red":
      return "/kurum#oneriler";
    case "firma_dogrulandi":
      return "/kurum/profil";
    // GİRVAK inceleme kuyruğu (docs/dogrulama.md § 9)
    case "inceleme_sonucu":
      return kart ? kartYolu(kart) : "/genc";
    case "ad_degisikligi_sonucu":
      return "/profil";
    case "hesap_baglama_sonucu":
      return "/profil#hesaplar";
    default:
      return "/bildirimler";
  }
}
