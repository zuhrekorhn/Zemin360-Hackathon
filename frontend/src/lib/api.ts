/**
 * Backend (FastAPI) ile konuşan ince bir fetch sarmalayıcısı.
 * Endpoint listesi: docs/api-contracts.md
 *
 * Token varsa her isteğe `Authorization: Bearer` eklenir (lib/token.ts).
 * 401 gelirse token silinir: süresi dolmuş ya da geçersiz; kullanıcı yeniden
 * giriş yapmalı (docs/faz-b-kimlik-ve-dongu.md § 1).
 */

import { tokenOku, tokenSil } from "@/lib/token";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiHatasi extends Error {
  /**
   * @param ayrinti Backend'in `{"detail": "..."}` gövdesindeki cümle. Ayrı
   *   tutuluyor ki `hatayaCevir` backend'in söylediğini kendi yedek
   *   cümlesinden ayırt edebilsin (lib/hata.ts).
   */
  constructor(
    message: string,
    readonly durumKodu?: number,
    readonly ayrinti?: string,
  ) {
    super(message);
    this.name = "ApiHatasi";
  }
}

export async function apiIstek<T>(
  yol: string,
  secenekler: RequestInit = {},
): Promise<T> {
  let yanit: Response;

  try {
    const token = tokenOku();
    yanit = await fetch(`${API_URL}${yol}`, {
      ...secenekler,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...secenekler.headers,
      },
    });
  } catch {
    // Ağ hatası / backend ayakta değil / CORS engeli
    throw new ApiHatasi(`Backend'e ulaşılamadı (${API_URL})`);
  }

  if (yanit.status === 401) tokenSil();

  if (!yanit.ok) {
    // FastAPI hatayı {"detail": "..."} olarak döner; varsa onu göster.
    let ayrinti: string | undefined;
    try {
      const govde = (await yanit.json()) as { detail?: unknown };
      if (typeof govde.detail === "string") ayrinti = govde.detail;
    } catch {
      // gövde JSON değil — durum koduyla yetin
    }
    throw new ApiHatasi(
      ayrinti ?? `İstek başarısız: ${yanit.status} ${yanit.statusText}`,
      yanit.status,
      ayrinti,
    );
  }

  return (await yanit.json()) as T;
}

export type SaglikYaniti = { status: string };

/* --- Kimlik (docs/faz-b-kimlik-ve-dongu.md § 1) ---------------------------
   Tipler backend'deki app/schemas/auth.py ile birebir eşleşir. */

export type Rol = "genc" | "kurum" | "girvak";

export type TokenYaniti = {
  token: string;
  token_turu: "bearer";
  hesap_id: string;
  rol: Rol;
};

export type YetenekKartiOzeti = {
  id: string;
  rol_alani: string;
  deneyim_seviyesi: string;
  kanit_bekleyen: boolean;
  embedding_var: boolean;
};

export type IhtiyacKartiOzeti = {
  id: string;
  problem_tanimi: string;
  olusturma_tarihi: string;
  embedding_var: boolean;
};

/** Giriş yapmış hesap; kart ve kurum kimliği buradan okunur. */
export type MeYaniti = {
  hesap_id: string;
  email: string;
  rol: Rol;
  ad: string | null;
  kullanici_id: string | null;
  kurum_id: string | null;
  yetenek_kartlari: YetenekKartiOzeti[];
  ihtiyac_kartlari: IhtiyacKartiOzeti[];
  okunmamis_bildirim: number;
};

/** GET /me — giriş yoksa 401 (token da silinir). */
export function me(): Promise<MeYaniti> {
  return apiIstek<MeYaniti>("/me", { cache: "no-store" });
}

/** GET /health — backend ayakta mı? */
export function saglikKontrol(): Promise<SaglikYaniti> {
  return apiIstek<SaglikYaniti>("/health", { cache: "no-store" });
}

/* --- Keşif Ajanı (docs/api-contracts.md § Keşif) --------------------------
   Tipler backend'deki app/schemas/kesif.py ile birebir eşleşir. */

export type SomutCiktiTaslagi = {
  baslik: string;
  aciklama: string | null;
  kanit_linki: string | null;
};

export type KartTaslagi = {
  rol_alani: string | null;
  deneyim_seviyesi: string | null;
  sektor_ilgi_alani: string[];
  araclar_teknolojiler: string[];
  somut_ciktilar: SomutCiktiTaslagi[];
};

export type SohbetYaniti = {
  oturum_id: string;
  /** Taslak hazırsa soru gelmez; beklenen şey onaydır. */
  soru: string | null;
  taslak: KartTaslagi;
  taslak_hazir: boolean;
};

/** Kart onayıyla gelen profil güncellemesi. Kimlik token'dan; ad ve e-posta
 *  kayıtta alındı. Boş bırakılan alan kayıtlı değeri silmez. */
export type GencProfili = {
  /** Profilde şehir yoksa onay 422 döner: eşleştirme şehre göre süzüyor. */
  sehir?: string | null;
  /** Kabul ettiği çalışma modelleri — çoklu seçim. */
  calisma_modelleri?: string[];
  musaitlik?: string | null;
};

export type SomutCiktiYaniti = {
  id: string;
  baslik: string;
  aciklama: string | null;
  kanit_linki: string | null;
  /** Doğrulama rubriği; hiç kanıt eklenmemişse null ("doğrulanmamış"). */
  guven_skoru: GuvenSkoru | null;
};

/** Kartın dışarıya açılan hali — e-posta/iletişim alanı taşımaz
 *  (docs/agent-specs.md § 1.5). */
export type YetenekKartiYaniti = {
  id: string;
  rol_alani: string;
  deneyim_seviyesi: string;
  sektor_ilgi_alani: string[];
  araclar_teknolojiler: string[];
  kanit_bekleyen: boolean;
  versiyon: number;
  embedding_var: boolean;
  somut_ciktilar: SomutCiktiYaniti[];
};

/** GET /yetenek-kartlari/{id} — kartın dışarıya açılan hali. */
export function yetenekKartiGetir(kartId: string): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(`/yetenek-kartlari/${kartId}`, {
    cache: "no-store",
  });
}

/** POST /yetenek-kartlari/{id}/embedding — onayda vektör servisine
 *  ulaşılamadıysa kartı eşleştirmeye hazırlar. */
export function yetenekKartiHazirla(
  kartId: string,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(`/yetenek-kartlari/${kartId}/embedding`, {
    method: "POST",
  });
}

/** POST /kesif/sohbet/baslat — yeni oturum açar, açılış sorusunu döner. */
export function sohbetBaslat(): Promise<SohbetYaniti> {
  return apiIstek<SohbetYaniti>("/kesif/sohbet/baslat", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** POST /kesif/sohbet/cevap — cevabı işler, sıradaki soruyu ya da taslağı döner. */
export function sohbetCevap(
  oturumId: string,
  cevap: string,
): Promise<SohbetYaniti> {
  return apiIstek<SohbetYaniti>("/kesif/sohbet/cevap", {
    method: "POST",
    body: JSON.stringify({ oturum_id: oturumId, cevap }),
  });
}

/** POST /kesif/kart/onayla — taslağı YETENEK_KARTI'na yazar. */
export function kartOnayla(
  oturumId: string,
  profil: GencProfili,
  duzeltilmisTaslak?: KartTaslagi,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>("/kesif/kart/onayla", {
    method: "POST",
    body: JSON.stringify({
      oturum_id: oturumId,
      profil,
      duzeltilmis_taslak: duzeltilmisTaslak ?? null,
    }),
  });
}

/* --- Tanımlama Ajanı (docs/api-contracts.md § Tanımlama) ------------------
   Tipler backend'deki app/schemas/tanimlama.py ile birebir eşleşir. */

export type IhtiyacTaslagi = {
  problem_tanimi: string | null;
  basari_kriteri: string | null;
  kisitlar: string | null;
  sehir_tercihi: string | null;
  /** Tek seçim: is_yerinde | hibrit | uzaktan. */
  calisma_modeli: string | null;
  musaitlik_tercihi: string | null;
};

export type TanimlamaSohbetYaniti = {
  oturum_id: string;
  soru: string | null;
  taslak: IhtiyacTaslagi;
  taslak_hazir: boolean;
};

/** İhtiyaç kartı onayıyla gelen kurum profili; ad ve e-posta kayıtta alındı. */
export type KurumProfili = {
  sektor?: string | null;
  sehir?: string | null;
};

/** Kartla gösterilen kurum bilgisi — iletişim e-postası taşımaz.
 *  `id` öneri uç noktası için gerekli (`/eslestirme/oneriler/{kurum_id}`). */
export type KurumYaniti = {
  id: string;
  ad: string;
  sektor: string | null;
  sehir: string | null;
};

export type IhtiyacKartiYaniti = {
  id: string;
  problem_tanimi: string;
  basari_kriteri: string | null;
  kisitlar: string | null;
  sehir_tercihi: string | null;
  calisma_modeli: string | null;
  musaitlik_tercihi: string | null;
  embedding_var: boolean;
  kurum: KurumYaniti;
};

/** POST /ihtiyac-kartlari/{id}/embedding — kartı eşleştirmeye hazırlar;
 *  başarılıysa eşleştirme de arka planda başlar. */
export function ihtiyacKartiHazirla(
  kartId: string,
): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>(`/ihtiyac-kartlari/${kartId}/embedding`, {
    method: "POST",
  });
}

/** POST /tanimlama/sohbet/baslat */
export function tanimlamaBaslat(): Promise<TanimlamaSohbetYaniti> {
  return apiIstek<TanimlamaSohbetYaniti>("/tanimlama/sohbet/baslat", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** POST /tanimlama/sohbet/cevap */
export function tanimlamaCevap(
  oturumId: string,
  cevap: string,
): Promise<TanimlamaSohbetYaniti> {
  return apiIstek<TanimlamaSohbetYaniti>("/tanimlama/sohbet/cevap", {
    method: "POST",
    body: JSON.stringify({ oturum_id: oturumId, cevap }),
  });
}

/** POST /tanimlama/kart/onayla — taslağı IHTIYAC_KARTI'na yazar. */
export function ihtiyacKartiOnayla(
  oturumId: string,
  kurumProfili: KurumProfili,
  duzeltilmisTaslak?: IhtiyacTaslagi,
): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>("/tanimlama/kart/onayla", {
    method: "POST",
    body: JSON.stringify({
      oturum_id: oturumId,
      kurum_profili: kurumProfili,
      duzeltilmis_taslak: duzeltilmisTaslak ?? null,
    }),
  });
}

/* --- Doğrulama Ajanı (docs/api-contracts.md § Doğrulama) -----------------
   Tipler backend'deki app/schemas/dogrulama.py ile birebir eşleşir. */

/** Dört bileşenli güven göstergesi. Tek sayıya indirgenmez
 *  (docs/agent-specs.md § 4) — arayüz de dördünü ayrı gösterir. */
export type GuvenSkoru = {
  kanit_orijinalligi: number;
  sonuc_olculebilirligi: number;
  rol_netligi: number;
  ucuncu_taraf_onayi: number;
  gerekce_metni: string | null;
};

export type ReferansDurumu = {
  id: string;
  referans_email: string;
  /** "bekliyor" | "yanitlandi" | "yanit_yok" — yanıt geldi demek, olumlu demek değil. */
  durum: string;
  puan: number | null;
  yanit_metni: string | null;
  olusturma_tarihi: string;
  /** SMTP yok (MVP): link burada dönüyor, iddia sahibi elle iletiyor. */
  yanit_linki: string | null;
};

export type KanitDurumu = {
  somut_cikti_id: string;
  baslik: string;
  kanit_linki: string | null;
  link_erisilebilir: boolean | null;
  guven_skoru: GuvenSkoru | null;
  referanslar: ReferansDurumu[];
};

export type KanitEkleGirdisi = {
  somut_cikti_id: string;
  kanit_linki?: string | null;
  kanit_turu?: string | null;
  referans_email?: string | null;
};

/** Referans kişinin yanıt vermeden önce gördüğü bilgi — iletişim bilgisi yok. */
export type ReferansIstegiBilgisi = {
  somut_cikti_id: string;
  baslik: string;
  aciklama: string | null;
  iddia_sahibi_adi: string;
  durum: string;
  yanitlanabilir: boolean;
};

/** GET /dogrulama/referans/{token} — girişsiz; zaman aşımı okuma anında işler. */
export function referansIstegiGetir(
  token: string,
): Promise<ReferansIstegiBilgisi> {
  return apiIstek<ReferansIstegiBilgisi>(
    `/dogrulama/referans/${encodeURIComponent(token)}`,
    { cache: "no-store" },
  );
}

/** POST /dogrulama/kanit-ekle — kanıtı kaydeder, ön rubriği üretir. */
export function kanitEkle(girdi: KanitEkleGirdisi): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>("/dogrulama/kanit-ekle", {
    method: "POST",
    body: JSON.stringify(girdi),
  });
}

/** GET /dogrulama/kanit/{id} — zaman aşımı bu okuma anında hesaplanır. */
export function kanitDurumu(somutCiktiId: string): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`/dogrulama/kanit/${somutCiktiId}`, {
    cache: "no-store",
  });
}

/** POST /dogrulama/itiraz — rubriği yeniden hesaplatır. */
export function itirazEt(
  somutCiktiId: string,
  yeniKanitLinki?: string | null,
  aciklama?: string | null,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>("/dogrulama/itiraz", {
    method: "POST",
    body: JSON.stringify({
      somut_cikti_id: somutCiktiId,
      yeni_kanit_linki: yeniKanitLinki ?? null,
      aciklama: aciklama ?? null,
    }),
  });
}

/** Referans yanıtından sonra dönen tek bilgi. Girişsiz uç nokta olduğu için
 *  diğer referansların e-postası, puanı ya da token'ı burada yok. */
export type ReferansYanitiSonucu = {
  baslik: string;
  durum: string;
};

/** POST /dogrulama/referans-yaniti — girişsiz, token bazlı. */
export function referansYanitla(
  token: string,
  puan: number,
  yorum?: string | null,
): Promise<ReferansYanitiSonucu> {
  return apiIstek<ReferansYanitiSonucu>("/dogrulama/referans-yaniti", {
    method: "POST",
    body: JSON.stringify({ token, puan, yorum: yorum ?? null }),
  });
}

/* --- Eşleştirme Ajanı (docs/api-contracts.md § Eşleştirme) ----------------
   Tipler backend'deki app/schemas/eslestirme.py ile birebir eşleşir. */

export type Oneri = {
  eslesme_id: string;
  /** 0-1 arası; docs/matching-algorithm.md § 4 formülü. */
  skor: number;
  /** "onerildi" | "ilgileniliyor" | "kabul_edildi" | "reddedildi" */
  durum: string;
  /** Gerekçe yoksa null: dil modeli o an yanıt vermedi ya da kanıtı
   *  olduğundan güçlü anlattığı için gerekçe bırakıldı. Skor yine de geçerli. */
  gerekce_metni: string | null;
  yetenek_karti: YetenekKartiYaniti;
};

export type Oneriler = {
  ihtiyac_karti_id: string;
  oneriler: Oneri[];
  /** Havuz küçükken gizlenmez, açıkça söylenir (matching-algorithm.md § 5). */
  az_sonuc_uyarisi: boolean;
  /** Eşik backend'den gelir; arayüzde sabitlenmez. */
  skor_esigi: number;
};

export type IlgileniyorumYaniti = {
  eslesme_id: string;
  durum: string;
  isbirligi_id: string;
  isbirligi_durum: string;
};

/** GET /eslestirme/oneriler/{kurum_id} — hesaplanmış listeyi okur.
 *  Kayıt varsa yeniden hesaplamaz; tazelemek için `eslestirmeCalistir`. */
export function eslestirmeOnerileri(kurumId: string): Promise<Oneriler> {
  return apiIstek<Oneriler>(`/eslestirme/oneriler/${kurumId}`, {
    cache: "no-store",
  });
}

/**
 * POST /eslestirme/calistir — pipeline'ı yeniden çalıştırır: skorlar tazelenir,
 * eksik gerekçeler üretilir, artık uygun olmayan öneriler listeden düşer.
 * Kurumun karar verdiği eşleşmelere dokunulmaz.
 */
export function eslestirmeCalistir(): Promise<Oneriler> {
  // Kurum token'dan belli; gövdede kurum_id yalnızca GİRVAK için.
  return apiIstek<Oneriler>("/eslestirme/calistir", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** POST /eslestirme/ilgileniyorum — eşleşmeyi kabul eder, iş birliğini açar. */
export function ilgileniyorum(eslesmeId: string): Promise<IlgileniyorumYaniti> {
  return apiIstek<IlgileniyorumYaniti>("/eslestirme/ilgileniyorum", {
    method: "POST",
    body: JSON.stringify({ eslesme_id: eslesmeId }),
  });
}

export { API_URL };
