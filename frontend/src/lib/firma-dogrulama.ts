/**
 * Firma doğrulaması (docs/plans/firma-akisi.md § 0 karar 6, § 6).
 * Saf fonksiyonlar; testleri firma-dogrulama.test.ts'de.
 *
 * İpucu sistemin önerisi, karar GİRVAK'ın. İpucu siteye bağlanmadan, yalnızca
 * e-posta uzantısıyla web sitesinin adresi karşılaştırılarak üretilir.
 */

export type AlanAdiIpucu =
  "uyusuyor" | "uyusmuyor" | "ucretsiz_eposta" | "site_yok" | "eposta_yok";

/** GİRVAK'a gösterilen ipucu cümlesi; `olumlu` yalnızca görsel vurgu için. */
export function ipucuMetni(
  ipucu: AlanAdiIpucu,
  epostaAlanAdi: string | null,
): { metin: string; olumlu: boolean } {
  switch (ipucu) {
    case "uyusuyor":
      return {
        metin: `E-posta uzantısı (${epostaAlanAdi}) web sitesiyle uyuşuyor.`,
        olumlu: true,
      };
    case "uyusmuyor":
      return {
        metin: `E-posta uzantısı (${epostaAlanAdi}) web sitesiyle uyuşmuyor.`,
        olumlu: false,
      };
    case "ucretsiz_eposta":
      return {
        metin: `Herkese açık bir e-posta servisi kullanılmış (${epostaAlanAdi}); uzantı firmayı göstermiyor.`,
        olumlu: false,
      };
    case "site_yok":
      return {
        metin: "Web sitesi yazılmamış; e-posta uzantısı karşılaştırılamadı.",
        olumlu: false,
      };
    case "eposta_yok":
      return { metin: "Kayıtlı bir e-posta yok.", olumlu: false };
  }
}

export const DOGRULANMIS_FIRMA = "Doğrulanmış firma";
