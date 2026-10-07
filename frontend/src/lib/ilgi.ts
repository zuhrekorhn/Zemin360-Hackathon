/**
 * İlgi akışının arayüz kararları (docs/kimlik-ve-dongu.md § 5, § 7).
 * Saf fonksiyonlar; testleri ilgi.test.ts'de. Metinler docs/icerik-rehberi.md'ye
 * göre: durum etiketleri § 5.9'daki tablo, açıklama başlığı "Neden uygun?".
 */

/** Rehber § 5.9, "Genç görür" sütunu. Gence "reddedildi" gösterilmez. */
const GENC_ETIKETLERI: Record<string, string> = {
  onerildi: "Sana uygun",
  genc_ilgilendi: "İlgin iletildi",
  ilgileniliyor: "Firma seninle ilgileniyor",
  kabul_edildi: "Karşılıklı ilgi",
  reddedildi: "Kapandı",
  kapandi: "Kapandı",
};

/** Rehber § 5.9, "Firma görür" sütunu. */
const FIRMA_ETIKETLERI: Record<string, string> = {
  onerildi: "Aday",
  genc_ilgilendi: "İlgi gösterdi",
  ilgileniliyor: "Yanıt bekleniyor",
  kabul_edildi: "Karşılıklı ilgi",
  reddedildi: "Kapandı",
  kapandi: "Kapandı",
};

// Kod değeri (ör. "genc_ilgilendi") kullanıcıya hiç gösterilmez (rehber § 4).
const BILINMEYEN = "Durumu güncelleniyor";

export function gencDurumEtiketi(durum: string): string {
  return GENC_ETIKETLERI[durum] ?? BILINMEYEN;
}

export function firmaDurumEtiketi(durum: string): string {
  return FIRMA_ETIKETLERI[durum] ?? BILINMEYEN;
}

/** Eşleşme açıklamasının başlığı; genç ve firma ekranında aynı (rehber § 9.2). */
export const NEDEN_UYGUN = "Neden uygun?";

/** "%72 uyum" (rehber § 4 ve § 6: yüzde işareti sayıdan önce). */
export function uyumMetni(skor: number): string {
  return `%${Math.round(skor * 100)} uyum`;
}

/**
 * Gencin "İlgileniyorum" onayı. Açık onay: firma da ilgilenirse e-posta ayrıca
 * sorulmadan paylaşılır (docs/kararlar.md G1). Düğme onay kutusu işaretlenmeden açılmaz.
 */
export const ILETISIM_ONAYI =
  "Firma da ilgilenirse e-posta adresin, sana ayrıca sorulmadan firmayla paylaşılır.";
export const ILETISIM_ONAYI_KUTUSU = "Bunu onaylıyorum";

/** Gencin bir satırda yapabilecekleri. */
export function gencEylemleri(durum: string): {
  ilgiGoster: boolean;
  geriCek: boolean;
} {
  return {
    ilgiGoster: durum === "onerildi",
    // Karşılıklı hâle gelmeden önce (backend de aynı kuralı işletir).
    geriCek: durum === "genc_ilgilendi",
  };
}

/** Firmanın bir aday satırında yapabilecekleri. */
export function firmaEylemleri(durum: string): {
  ilgileniyorum: boolean;
  simdilikDegil: boolean;
} {
  return {
    ilgileniyorum: durum === "onerildi" || durum === "genc_ilgilendi",
    simdilikDegil: durum === "genc_ilgilendi",
  };
}

/** Firmanın listesi: ilgi gösterenler ayrı bölümde, sıralama (uyum) değişmez. */
export function ilgiGosterenleriAyir<T extends { durum: string }>(
  oneriler: T[],
): { ilgiGosterenler: T[]; digerleri: T[] } {
  return {
    ilgiGosterenler: oneriler.filter((o) => o.durum === "genc_ilgilendi"),
    digerleri: oneriler.filter((o) => o.durum !== "genc_ilgilendi"),
  };
}

/** Önerinin adayının adı: gencin adı ya da firmanın adı. */
export function onerininAdayAdi(oneri: {
  yetenek_karti: { genc_adi: string } | null;
  firma_karti: { firma_adi: string } | null;
}): string {
  return oneri.firma_karti?.firma_adi ?? oneri.yetenek_karti?.genc_adi ?? "";
}
