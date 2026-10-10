/**
 * Canlılık ve GİRVAK paneli görünüm kuralları (docs/canlilik.md § 7).
 * Kural backend'de (app/agents/canlilik_kurallari.py); burada yalnızca
 * "ekranda ne yazsın". Testleri canlilik.test.ts'de.
 */

export const CANLILIK_TUR_ETIKETLERI: Record<string, string> = {
  oneri_bekliyor: "Bakılmayan öneri",
  ilgi_yanitsiz_1: "Yanıtsız ilgi",
  ilgi_yanitsiz_2: "Yanıtsız ilgi (son hatırlatma)",
  plan_onaysiz: "Onaylanmayan plan",
  isbirligi_hareketsiz: "İlerlemeyen iş birliği",
  adim_gecikti: "Gecikmiş adım",
  yeni_firsat: "Gence yeni fırsat bildirimi",
  // Genç akışı: genç ilgi gösterdi, firma yanıt vermedi (GİRVAK panelinde).
  genc_ilgisi_yanitsiz: "Yanıtsız genç ilgisi",
  // Doğrulama: tarama özetinde görünen sayaçlar (olay değil).
  referans_hatirlatma: "Referans hatırlatması",
  referans_yanit_yok: "Yanıtsız referans",
  link_yoklandi: "Kontrol edilen kanıt linki",
  link_curudu: "Açılmayan kanıt linki",
};

export function turEtiketi(tur: string): string {
  return CANLILIK_TUR_ETIKETLERI[tur] ?? tur;
}

/**
 * Takılma süreleri (gün). Kaynak backend `canlilik_kurallari.ESIKLER`; orada
 * değişirse bu cümle de değişmeli (docs/canlilik.md § 1).
 */
export const TAKILMA_SURELERI =
  "Takılma süreleri: öneri 7 gün, ilgiye yanıt 3 gün, plan onayı 5 gün, iş birliği 14 gün; adım, hedef tarihinden bir gün sonra.";

const ROL_ADLARI: Record<string, string> = { genc: "genç", kurum: "firma" };

/** ["genc", "kurum"] → "genç ve kurum" */
export function alicilarMetni(alicilar: string[]): string {
  const adlar = alicilar.map((a) => ROL_ADLARI[a] ?? a);
  return adlar.length > 1
    ? `${adlar.slice(0, -1).join(", ")} ve ${adlar[adlar.length - 1]}`
    : (adlar[0] ?? "");
}

/** Pasif satırının süre cümlesi: gecikmede hedeften, diğerlerinde hareketten beri. */
export function pasifSureMetni(tur: string, gun: number): string {
  return tur === "adim_gecikti"
    ? `hedef tarihi ${gun} gün geçti`
    : `${gun} gündür ilerleme yok`;
}
