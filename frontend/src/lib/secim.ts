/**
 * Çoklu seçim (çalışma modeli, müsaitlik) için saf yardımcı.
 *
 * Sonuç seçeneklerin kendi sırasında ve tekrarsız döner: backend de kodları
 * sabit sırada saklıyor, kullanıcının tıklama sırası bir anlam taşımıyor.
 */
export function secimiDegistir(
  secenekler: readonly string[],
  secili: readonly string[],
  deger: string,
): string[] {
  const yeni = new Set(secili);
  if (yeni.has(deger)) yeni.delete(deger);
  else yeni.add(deger);
  return secenekler.filter((secenek) => yeni.has(secenek));
}
