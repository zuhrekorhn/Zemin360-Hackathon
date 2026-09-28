/**
 * Girişe ve role göre yönlendirme kuralları (docs/faz-b-kimlik-ve-dongu.md § 7).
 * Saf fonksiyonlar; testleri yonlendirme.test.ts'de.
 */

import type { Rol } from "@/lib/api";

/** Her rolün paneli: giriş sonrası ve rolü uymayan sayfadan buraya gidilir. */
export function panelYolu(rol: Rol): string {
  if (rol === "genc") return "/genc";
  if (rol === "kurum") return "/kurum";
  return "/girvak";
}

const GIRIS_SAYFALARI = ["/giris", "/kayit"];

/** Canlılık'ın iş birliğine bağlı hatırlatmaları (Faz D): iş birliği sayfasına. */
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
 * Kayıttan sonra nereye (docs/plans/genc-akisi.md § 5.2): genç doğrudan Keşif
 * sohbetine (onboarding; "Şimdilik atla" oradan panele), diğerleri panele.
 * Güvenli bir `sonra` varsa o öncelikli.
 */
export function kayittanSonra(rol: Rol, sonra: string | null): string {
  const hedef = guvenliSonra(sonra);
  if (hedef) return hedef;
  return rol === "genc" ? "/kesif?ilk=1" : panelYolu(rol);
}

/**
 * Bildirime tıklayınca nereye (docs/faz-b-kimlik-ve-dongu.md § 6).
 * Gence gidenler (ilgi, referans yanıtı) genç paneline; kuruma gidenler
 * (yeni öneri, red) kurum paneline. İş birliği olan bildirim (kabul ve
 * Takip'in bütün türleri, Faz C) doğrudan iş birliği sayfasına. Bilinmeyen
 * tür (Faz D'de eklenecekler) bildirim sayfasında kalır.
 */
export function bildirimHedefi(
  tur: string,
  isbirligiId: string | null = null,
  rol: Rol | null = null,
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
  switch (tur) {
    // Canlılık (Faz D). Yanıtsız ilginin son hatırlatması iki tarafa aynı
    // türle gider: genç ilgiler bölümüne, kurum önerilerine.
    case "oneri_bekliyor":
      return "/kurum#ihtiyaclar";
    case "ilgi_yanitsiz_1":
      return "/genc#ilgiler";
    case "ilgi_yanitsiz_2":
      return rol === "kurum" ? "/kurum#oneriler" : "/genc#ilgiler";
    case "yeni_firsat":
      return "/genc#firsatlar";
    // Gençten ilgi (docs/plans/genc-akisi.md § 7.1)
    case "genc_ilgi":
      return "/kurum#ihtiyaclar";
    case "karsilikli_ilgi":
    case "firsat_kapandi":
      return "/genc#ilgilerim";
    case "ilgi":
      return "/genc#ilgiler";
    case "referans_yaniti":
      return "/genc#kartlar";
    case "yeni_oneri":
      return "/kurum#ihtiyaclar";
    case "kabul":
      return "/kurum#isbirlikleri";
    case "red":
      return "/kurum#oneriler";
    default:
      return "/bildirimler";
  }
}
