/**
 * Canlılık ve GİRVAK paneli görünüm kuralları (docs/faz-d-canlilik.md § 7).
 * Kural backend'de (app/agents/canlilik_kurallari.py); burada yalnızca
 * "ekranda ne yazsın". Testleri canlilik.test.ts'de.
 */

export const CANLILIK_TUR_ETIKETLERI: Record<string, string> = {
  oneri_bekliyor: "Bakılmayan öneri",
  ilgi_yanitsiz_1: "Yanıtsız ilgi",
  ilgi_yanitsiz_2: "Yanıtsız ilgi (son hatırlatma)",
  plan_onaysiz: "Onaylanmayan plan",
  isbirligi_hareketsiz: "Hareketsiz iş birliği",
  adim_gecikti: "Gecikmiş adım",
  yeni_firsat: "Yeni fırsat",
  // Genç akışı: genç ilgi gösterdi, firma yanıt vermedi (GİRVAK panelinde).
  genc_ilgisi_yanitsiz: "Yanıtsız genç ilgisi",
};

export function turEtiketi(tur: string): string {
  return CANLILIK_TUR_ETIKETLERI[tur] ?? tur;
}

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
    : `${gun} gündür hareket yok`;
}

/** Hedef ilerlemesi 0-100 (hedef aşıldıysa 100'de durur; çizgi taşmasın). */
export function hedefYuzdesi(sayi: number, hedef: number): number {
  if (hedef <= 0) return 0;
  return Math.min(100, Math.round((sayi / hedef) * 100));
}

/** "80 startup başvurusu" — programın kendi adıyla hedef. */
export function hedefBasligi(hedef: number, programAdi: string): string {
  return `${hedef} ${programAdi}`;
}
