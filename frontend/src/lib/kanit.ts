/**
 * Kanıt parçalarının görünüm mantığı (docs/plans/dogrulama-iyilestirme.md § 2, § 3).
 * Saf fonksiyonlar; testleri kanit.test.ts'de.
 */

import type {
  GuvenSkoru,
  KanitParcasi,
  SomutCiktiTaslagi,
  SomutCiktiYaniti,
} from "@/lib/api";

/** Şeması olmayan linke https:// ekler (genç linki çoğu zaman şemasız yazıyor). */
export function kanitAdresi(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url.replace(/^\/+/, "")}`;
}

/** Link türündeki, adresi olan parçalar (eklenme sırasıyla). */
export function kanitLinkleri(
  kanitlar: KanitParcasi[],
): (KanitParcasi & { url: string })[] {
  return kanitlar.filter(
    (parca): parca is KanitParcasi & { url: string } =>
      parca.tur === "link" && Boolean(parca.url),
  );
}

/**
 * Çalışma değerlendirildi mi? Kanıt, Sonuç ya da Rol'den biri doluysa evet.
 * Yalnızca Referans doluysa (linksiz kalemde referans yanıt verdi) hayır:
 * kanıt henüz değerlendirilmedi.
 */
export function degerlendirildiMi(
  skor: GuvenSkoru | null | undefined,
): boolean {
  if (!skor) return false;
  return [
    skor.kanit_orijinalligi,
    skor.sonuc_olculebilirligi,
    skor.rol_netligi,
  ].some((deger) => deger !== null);
}

/** Kayıtlı çalışmayı taslak önizlemesinin biçimine çevirir (önizleme tek link gösterir). */
export function kayitliCiktiTaslagi(
  cikti: SomutCiktiYaniti,
): SomutCiktiTaslagi {
  return {
    baslik: cikti.baslik,
    aciklama: cikti.aciklama,
    kanit_linki: kanitLinkleri(cikti.kanitlar)[0]?.url ?? null,
    is_turu: cikti.is_turu ?? null,
    olculebilir_sonuc: cikti.olculebilir_sonuc ?? null,
    kendi_rolu: cikti.kendi_rolu ?? null,
  };
}
