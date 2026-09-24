/**
 * Backend (FastAPI) ile konuşan ince bir fetch sarmalayıcısı.
 * Endpoint listesi: docs/api-contracts.md
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiHatasi extends Error {
  constructor(
    message: string,
    readonly durumKodu?: number,
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
    yanit = await fetch(`${API_URL}${yol}`, {
      ...secenekler,
      headers: {
        "Content-Type": "application/json",
        ...secenekler.headers,
      },
    });
  } catch {
    // Ağ hatası / backend ayakta değil / CORS engeli
    throw new ApiHatasi(`Backend'e ulaşılamadı (${API_URL})`);
  }

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
    );
  }

  return (await yanit.json()) as T;
}

export type SaglikYaniti = { status: string };

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

export type KullaniciGirdisi = {
  ad: string;
  email: string;
  sehir?: string | null;
  musaitlik?: string | null;
};

export type SomutCiktiYaniti = {
  id: string;
  baslik: string;
  aciklama: string | null;
  kanit_linki: string | null;
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
  kullanici: KullaniciGirdisi,
  duzeltilmisTaslak?: KartTaslagi,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>("/kesif/kart/onayla", {
    method: "POST",
    body: JSON.stringify({
      oturum_id: oturumId,
      kullanici,
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
  musaitlik_tercihi: string | null;
};

export type TanimlamaSohbetYaniti = {
  oturum_id: string;
  soru: string | null;
  taslak: IhtiyacTaslagi;
  taslak_hazir: boolean;
};

export type KurumGirdisi = {
  ad: string;
  sektor?: string | null;
  sehir?: string | null;
  iletisim_email: string;
};

/** Kartla gösterilen kurum bilgisi — iletişim e-postası taşımaz. */
export type KurumYaniti = {
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
  musaitlik_tercihi: string | null;
  embedding_var: boolean;
  kurum: KurumYaniti;
};

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
  kurum: KurumGirdisi,
  duzeltilmisTaslak?: IhtiyacTaslagi,
): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>("/tanimlama/kart/onayla", {
    method: "POST",
    body: JSON.stringify({
      oturum_id: oturumId,
      kurum,
      duzeltilmis_taslak: duzeltilmisTaslak ?? null,
    }),
  });
}

export { API_URL };
