/**
 * Backend (FastAPI) ile konuşan ince bir fetch sarmalayıcısı.
 * Endpoint listesi: docs/api-contracts.md
 *
 * Token varsa her isteğe `Authorization: Bearer` eklenir (lib/token.ts).
 * 401 gelirse token silinir: süresi dolmuş ya da geçersiz; kullanıcı yeniden
 * giriş yapmalı (docs/kimlik-ve-dongu.md § 1).
 */

import type { AlanAdiIpucu } from "@/lib/firma-dogrulama";
import { ayrintiyiOku } from "@/lib/ayrinti";
import type { KapanmaNedeni } from "@/lib/ilan";
import type { Uygunluk } from "@/lib/uygunluk";
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
    // Dosya yüklemede tarayıcı multipart sınırını kendisi yazar.
    const formMu = secenekler.body instanceof FormData;
    yanit = await fetch(`${API_URL}${yol}`, {
      ...secenekler,
      headers: {
        ...(formMu ? {} : { "Content-Type": "application/json" }),
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
      ayrinti = ayrintiyiOku(govde.detail);
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

/* --- Kimlik (docs/kimlik-ve-dongu.md § 1) ---------------------------
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
  /** acik | kapandi (docs/kararlar.md F7) */
  durum: string;
  /** genc | firma: hangi kapıdan açıldı */
  aranan: "genc" | "firma";
  basari_kriteri?: string | null;
};

/** Giriş yapmış hesap; kart ve kurum kimliği buradan okunur. */
export type MeYaniti = {
  hesap_id: string;
  email: string;
  rol: Rol;
  ad: string | null;
  kullanici_id: string | null;
  kurum_id: string | null;
  /** Gencin tek kartı (G17); Keşif'i tamamlamadıysa null. */
  yetenek_karti: YetenekKartiOzeti | null;
  ihtiyac_kartlari: IhtiyacKartiOzeti[];
  okunmamis_bildirim: number;
  /** Genç ve firma: doldurulması gereken zorunlu profil alanları (eski hesaplar için bant). */
  eksik_profil_alanlari: string[];
  /** Genç ve firma: KVKK aydınlatma metni onaylı mı? GİRVAK'ta true. */
  kvkk_onayli: boolean;
  /** Firma: firma kartı var mı? (panel çağrısı) */
  firma_karti_var: boolean;
  /** Kayıt e-postası doğrulandı mı? Doğrulanmamış hesap her şeyi kullanır, panelde bant görür. */
  eposta_dogrulandi: boolean;
};

/* --- E-posta doğrulama (docs/dogrulama.md § 6.3) -------- */

/** Bağlantıdaki token'la doğrular; giriş gerekmez. Tekrarı da başarılı döner. */
export function epostaDogrula(
  token: string,
): Promise<{ eposta_dogrulandi: boolean }> {
  return apiIstek("/auth/eposta-dogrula", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

/** Yeni doğrulama bağlantısı gönderir (eskisi geçersiz olur). */
export async function dogrulamaBaglantisiGonder(): Promise<void> {
  await apiIstek("/auth/eposta-dogrulama/yeniden", { method: "POST" });
}

/* --- Genç profili (docs/agent-specs.md § 1, § 6.1) ------------------
   Tipler backend'deki app/schemas/profil.py ile birebir eşleşir. */

export type KariyerDurumu = "ogrenci" | "mezun" | "calisiyor";

/** Kayıt formunun genç kısmı. Fotoğraf, yaş, cinsiyet gibi alanlar bilinçli yok. */
export type GencKayitProfili = {
  sehir: string;
  calisma_modelleri: string[];
  kariyer_durumu: KariyerDurumu;
  musaitlikler: string[];
  musaitlik_baslangici?: string | null;
  okul?: string | null;
  bolum?: string | null;
  sinif?: number | null;
  mezuniyet_yili?: number | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  portfolyo_url?: string | null;
};

export type GencProfil = {
  ad: string;
  email: string;
  sehir: string | null;
  calisma_modelleri: string[];
  kariyer_durumu: KariyerDurumu | null;
  musaitlikler: string[];
  musaitlik_baslangici: string | null;
  okul: string | null;
  bolum: string | null;
  sinif: number | null;
  mezuniyet_yili: number | null;
  github_url: string | null;
  linkedin_url: string | null;
  portfolyo_url: string | null;
  kvkk_onay_tarihi: string | null;
  eksik_alanlar: string[];
  /** E-posta doğrulanınca ad kilitlenir; değişiklik GİRVAK'a talep olarak gider. */
  ad_kilitli: boolean;
  /** Bekleyen ad değişikliği talebinin istediği ad. */
  bekleyen_ad: string | null;
};

/** PATCH /profil: yalnızca gönderilen alan değişir; opsiyonel alan null ya da "" ile silinir. */
export type GencProfilGuncelleme = Partial<
  Omit<
    GencProfil,
    | "email"
    | "kvkk_onay_tarihi"
    | "eksik_alanlar"
    | "ad_kilitli"
    | "bekleyen_ad"
  >
> & { kvkk_onay?: boolean };

/** Kilitli ad için GİRVAK'a değişiklik talebi (docs/dogrulama.md § 6.3). */
export function adDegisikligiIste(
  yeniAd: string,
  gerekce: string | null,
): Promise<GencProfil> {
  return apiIstek<GencProfil>("/profil/ad-degisikligi", {
    method: "POST",
    body: JSON.stringify({ yeni_ad: yeniAd, gerekce }),
  });
}

/** GET /profil — gencin kendi profili. */
export function profilGetir(): Promise<GencProfil> {
  return apiIstek<GencProfil>("/profil");
}

/** PATCH /profil — zorunlu alan boşaltılamaz (422). */
export function profilGuncelle(
  girdi: GencProfilGuncelleme,
): Promise<GencProfil> {
  return apiIstek<GencProfil>("/profil", {
    method: "PATCH",
    body: JSON.stringify(girdi),
  });
}

/* --- Firma profili (docs/kararlar.md F2) ---------------------------
   Tipler backend'deki app/schemas/profil.py ile birebir eşleşir. */

export type FirmaTuru = "girisim" | "kobi" | "kurumsal";
export type CalisanAraligi = "1-10" | "11-50" | "51-250" | "250+";

/** Kayıt formunun firma kısmı. Vergi no, adres, telefon bilinçli yok. */
export type FirmaKayitProfili = {
  tur: FirmaTuru;
  sektor: string;
  sehir: string;
  web_sitesi?: string | null;
  calisan_araligi?: CalisanAraligi | null;
  kurulus_yili?: number | null;
  tanitim?: string | null;
  yetkili_ad?: string | null;
  yetkili_gorev?: string | null;
};

export type FirmaProfil = {
  ad: string;
  email: string | null;
  tur: FirmaTuru | null;
  sektor: string | null;
  sehir: string | null;
  web_sitesi: string | null;
  calisan_araligi: CalisanAraligi | null;
  kurulus_yili: number | null;
  tanitim: string | null;
  yetkili_ad: string | null;
  yetkili_gorev: string | null;
  kvkk_onay_tarihi: string | null;
  eksik_alanlar: string[];
  /** GİRVAK doğruladı mı? Web sitesi değişince yeniden beklenir. */
  dogrulandi: boolean;
};

/** PATCH /kurum/profil: yalnızca gönderilen alan değişir. */
export type FirmaProfilGuncelleme = Partial<
  Omit<
    FirmaProfil,
    "email" | "kvkk_onay_tarihi" | "eksik_alanlar" | "dogrulandi"
  >
> & { kvkk_onay?: boolean };

/** GET /kurum/profil — firmanın kendi profili. */
export function firmaProfiliGetir(): Promise<FirmaProfil> {
  return apiIstek<FirmaProfil>("/kurum/profil");
}

/** PATCH /kurum/profil — zorunlu alan boşaltılamaz (422). */
export function firmaProfiliGuncelle(
  girdi: FirmaProfilGuncelleme,
): Promise<FirmaProfil> {
  return apiIstek<FirmaProfil>("/kurum/profil", {
    method: "PATCH",
    body: JSON.stringify(girdi),
  });
}

/* --- Firma kartı (docs/kararlar.md F3) ---------------------------
   Tipler backend'deki app/schemas/firma_karti.py ile birebir eşleşir. */

export type FirmaKartiGirdisi = {
  ne_yapiyoruz: string;
  yetkinlikler: string[];
  onceki_isler: string | null;
  aranan_isbirligi: string | null;
  isbirligi_turleri: string[];
};

export type FirmaKartiYaniti = FirmaKartiGirdisi & {
  id: string;
  kurum_id: string;
  firma_adi: string;
  versiyon: number;
  /** Eşleştirmeye hazır mı (arka plan hazırlığı bitti mi)? */
  embedding_var: boolean;
  olusturma_tarihi: string;
  /** Aday olarak tamamladığı iş birliği sayısı; kart sayfasında rozet. */
  tamamlanan_isbirligi?: number;
};

export type FirmaKartiTaslagi = {
  ne_yapiyoruz: string | null;
  yetkinlikler: string[];
  onceki_isler: string | null;
  aranan_isbirligi: string | null;
  isbirligi_turleri: string[];
};

export type FirmaKartiSohbetYaniti = {
  oturum_id: string;
  soru: string | null;
  taslak: FirmaKartiTaslagi;
  taslak_hazir: boolean;
};

/** GET /kurum/kart — firmanın kartı; yoksa null. */
export function firmaKartim(): Promise<FirmaKartiYaniti | null> {
  return apiIstek<FirmaKartiYaniti | null>("/kurum/kart", {
    cache: "no-store",
  });
}

/** PATCH /kurum/kart — yalnızca gönderilen alan değişir. */
export function firmaKartiDuzenle(
  girdi: Partial<FirmaKartiGirdisi>,
): Promise<FirmaKartiYaniti> {
  return apiIstek<FirmaKartiYaniti>("/kurum/kart", {
    method: "PATCH",
    body: JSON.stringify(girdi),
  });
}

/** POST /kurum/kart/sohbet/baslat — kartı olan firma için 409. */
export function firmaKartiSohbetBaslat(): Promise<FirmaKartiSohbetYaniti> {
  return apiIstek<FirmaKartiSohbetYaniti>("/kurum/kart/sohbet/baslat", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** POST /kurum/kart/sohbet/cevap */
export function firmaKartiSohbetCevap(
  oturumId: string,
  cevap: string,
): Promise<FirmaKartiSohbetYaniti> {
  return apiIstek<FirmaKartiSohbetYaniti>("/kurum/kart/sohbet/cevap", {
    method: "POST",
    body: JSON.stringify({ oturum_id: oturumId, cevap }),
  });
}

/** POST /kurum/kart/onayla — taslağı (ya da düzeltilmiş hâlini) kaydeder. */
export function firmaKartiOnayla(
  oturumId: string,
  duzeltilmis: FirmaKartiGirdisi,
): Promise<FirmaKartiYaniti> {
  return apiIstek<FirmaKartiYaniti>("/kurum/kart/onayla", {
    method: "POST",
    body: JSON.stringify({
      oturum_id: oturumId,
      duzeltilmis_taslak: duzeltilmis,
    }),
  });
}

/** GET /me — giriş yoksa 401 (token da silinir). */
export function me(): Promise<MeYaniti> {
  return apiIstek<MeYaniti>("/me", { cache: "no-store" });
}

/** POST /auth/kayit — 201 + token; kayıtla birlikte giriş yapılmış olur.
 *  E-posta kayıtlıysa 409. GİRVAK açık kayıtla açılamaz. */
export function kayitOl(girdi: {
  email: string;
  sifre: string;
  rol: "genc" | "kurum";
  ad: string;
  /** Genç için zorunlu; kurum göndermez. */
  genc_profili?: GencKayitProfili;
  /** Firma için zorunlu; genç göndermez. */
  firma_profili?: FirmaKayitProfili;
  /** İki rol için de zorunlu (KVKK aydınlatma metni onayı). */
  kvkk_onay?: boolean;
}): Promise<TokenYaniti> {
  return apiIstek<TokenYaniti>("/auth/kayit", {
    method: "POST",
    body: JSON.stringify(girdi),
  });
}

/** POST /auth/giris — yanlış e-posta ya da şifre için tek bir 401 cümlesi. */
export function girisYap(email: string, sifre: string): Promise<TokenYaniti> {
  return apiIstek<TokenYaniti>("/auth/giris", {
    method: "POST",
    body: JSON.stringify({ email, sifre }),
  });
}

/* --- Bildirimler (docs/kimlik-ve-dongu.md § 6) ---------------------- */

export type BildirimTuru =
  | "yeni_oneri"
  | "ilgi"
  | "kabul"
  | "red"
  | "referans_yaniti"
  | "referans_yanit_yok";

export type Bildirim = {
  id: string;
  tur: BildirimTuru | string;
  metin: string;
  eslesme_id: string | null;
  /** Eşleşmenin iş birliği varsa: bildirim doğrudan iş birliği sayfasına gider. */
  isbirligi_id: string | null;
  olusturma_tarihi: string;
  okundu_tarihi: string | null;
};

export function bildirimler(): Promise<Bildirim[]> {
  return apiIstek<Bildirim[]>("/bildirimler", { cache: "no-store" });
}

export function bildirimOkundu(id: string): Promise<Bildirim> {
  return apiIstek<Bildirim>(`/bildirimler/${id}/okundu`, { method: "POST" });
}

export function hepsiniOku(): Promise<{ okunan: number }> {
  return apiIstek<{ okunan: number }>("/bildirimler/hepsini-oku", {
    method: "POST",
  });
}

/** GET /health — backend ayakta mı? */
export function saglikKontrol(): Promise<SaglikYaniti> {
  return apiIstek<SaglikYaniti>("/health", { cache: "no-store" });
}

/* --- Keşif Ajanı (docs/api-contracts.md § Keşif) --------------------------
   Tipler backend'deki app/schemas/kesif.py ile birebir eşleşir. */

/** İş kalemi taslağı. Sonuç ve rol ayrı alanlar; referans e-postası onayda
 *  iş kalemine referans isteği olarak bağlanır (docs/agent-specs.md § 1). */
export type SomutCiktiTaslagi = {
  baslik: string;
  aciklama: string | null;
  kanit_linki: string | null;
  /** proje | staj | is | gonulluluk | yarisma */
  is_turu?: string | null;
  olculebilir_sonuc?: string | null;
  kendi_rolu?: string | null;
  referans_email?: string | null;
};

export type KartTaslagi = {
  rol_alani: string | null;
  deneyim_seviyesi: string | null;
  sektor_ilgi_alani: string[];
  araclar_teknolojiler: string[];
  sertifikalar?: string[];
  diller?: string[];
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
  /** Kabul ettiği çalışma tipleri — çoklu seçim (staj dahil). */
  musaitlikler?: string[];
};

export type SomutCiktiYaniti = {
  id: string;
  baslik: string;
  aciklama: string | null;
  /** Kanıt parçaları (link; ileride dosya ve görsel), eklenme sırasıyla. */
  kanitlar: KanitParcasi[];
  is_turu?: string | null;
  olculebilir_sonuc?: string | null;
  kendi_rolu?: string | null;
  /** Doğrulama rubriği; hiç kanıt eklenmemişse null ("doğrulanmamış"). */
  guven_skoru: GuvenSkoru | null;
};

/** Kartın dışarıya açılan hali — e-posta/iletişim alanı taşımaz
 *  (docs/agent-specs.md § 1.5). */
export type YetenekKartiYaniti = {
  id: string;
  /** Gencin adı iletişim bilgisi sayılmıyor, baştan görünür; e-posta
   *  yalnızca kabulden sonra `iletisim` alanında gelir. */
  genc_adi: string;
  rol_alani: string;
  deneyim_seviyesi: string;
  sektor_ilgi_alani: string[];
  araclar_teknolojiler: string[];
  sertifikalar: string[];
  diller: string[];
  kanit_bekleyen: boolean;
  versiyon: number;
  embedding_var: boolean;
  somut_ciktilar: SomutCiktiYaniti[];
  /** Tamamlanmış iş birliği sayısı; eşleşme skoruna bonus olarak girer. */
  tamamlanan_pilot: number;
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

/* --- Kart düzenleme (docs/agent-specs.md § 1) ---------------------------
   Yalnızca kartın sahibi. İçerik ya da link değişen iş kaleminin güven
   göstergesi sıfırlanır ve yeniden değerlendirilir. */

export type KartGuncelleme = Partial<{
  rol_alani: string;
  deneyim_seviyesi: string;
  sektor_ilgi_alani: string[];
  araclar_teknolojiler: string[];
  sertifikalar: string[];
  diller: string[];
}>;

export type IsKalemiGirdisi = {
  baslik: string;
  aciklama?: string | null;
  olculebilir_sonuc?: string | null;
  kendi_rolu?: string | null;
  /** Yeni çalışmada verilirse ilk kanıt parçası olur. */
  kanit_linki?: string | null;
  is_turu?: string | null;
};

/** İddianın düzenlenebilir alanları. Kanıt burada değil: kanıt bölümünden
 *  (tek kapı) eklenir ve kaldırılır. */
export type IsKalemiGuncellemesi = Partial<
  Omit<IsKalemiGirdisi, "kanit_linki">
>;

/** PATCH /yetenek-kartlari/{id} */
export function kartGuncelle(
  kartId: string,
  girdi: KartGuncelleme,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(`/yetenek-kartlari/${kartId}`, {
    method: "PATCH",
    body: JSON.stringify(girdi),
  });
}

/** POST /yetenek-kartlari/{id}/ciktilar */
export function isKalemiEkle(
  kartId: string,
  girdi: IsKalemiGirdisi,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(`/yetenek-kartlari/${kartId}/ciktilar`, {
    method: "POST",
    body: JSON.stringify(girdi),
  });
}

/** PATCH /yetenek-kartlari/{id}/ciktilar/{cid} — yalnızca gönderilen alan değişir. */
export function isKalemiGuncelle(
  kartId: string,
  ciktiId: string,
  girdi: IsKalemiGuncellemesi,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(
    `/yetenek-kartlari/${kartId}/ciktilar/${ciktiId}`,
    { method: "PATCH", body: JSON.stringify(girdi) },
  );
}

/** DELETE /yetenek-kartlari/{id}/ciktilar/{cid} */
export function isKalemiSil(
  kartId: string,
  ciktiId: string,
): Promise<YetenekKartiYaniti> {
  return apiIstek<YetenekKartiYaniti>(
    `/yetenek-kartlari/${kartId}/ciktilar/${ciktiId}`,
    { method: "DELETE" },
  );
}

/** POST /kesif/sohbet/baslat — yeni oturum açar, açılış sorusunu döner. */
export function sohbetBaslat(): Promise<SohbetYaniti> {
  return apiIstek<SohbetYaniti>("/kesif/sohbet/baslat", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** Yarım kalan sohbetin geri yüklenen hali: balonlar, bekleyen soru, taslak. */
export type SohbetDevamYaniti = SohbetYaniti & {
  mesajlar: { kim: "ajan" | "kullanici"; metin: string }[];
};

/** GET /kesif/sohbet/{id} — sayfa yenilenince sohbet kaldığı yerden sürer. */
export function sohbetDevam(oturumId: string): Promise<SohbetDevamYaniti> {
  return apiIstek<SohbetDevamYaniti>(`/kesif/sohbet/${oturumId}`, {
    cache: "no-store",
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

/** Başarı kriterinin parçaları (backend app/core/basari_olcutu.py). */
export type BasariOlcutu = {
  metrik?: string | null;
  mevcut_deger?: string | null;
  hedef_deger?: string | null;
  sure?: string | null;
  olcum_bilinmiyor?: boolean;
};

export type IhtiyacTaslagi = {
  problem_tanimi: string | null;
  basari_kriteri: string | null;
  basari_olcutu?: BasariOlcutu | null;
  kisitlar: string | null;
  sehir_tercihi: string | null;
  /** Tek seçim: is_yerinde | hibrit | uzaktan. */
  calisma_modeli: string | null;
  musaitlik_tercihi: string | null;
  /** Ortak ilanı (docs/kararlar.md F3); genç ilanında boş. */
  aranan_firma_turleri?: string[];
  isbirligi_turu?: string | null;
};

export type TanimlamaSohbetYaniti = {
  oturum_id: string;
  /** genc | firma: hangi kapıdan açıldı */
  aranan: "genc" | "firma";
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
  /** "Doğrulanmış firma" işareti (docs/kararlar.md F17). */
  dogrulandi: boolean;
};

export type IhtiyacKartiYaniti = {
  id: string;
  problem_tanimi: string;
  basari_kriteri: string | null;
  basari_olcutu: BasariOlcutu | null;
  /** Hedef değeri olmayan ölçüt: "Ölçüm yöntemi belirlenecek". */
  olcum_belirlenecek: boolean;
  kisitlar: string | null;
  sehir_tercihi: string | null;
  calisma_modeli: string | null;
  musaitlik_tercihi: string | null;
  embedding_var: boolean;
  kurum: KurumYaniti;
  /** acik | kapandi. Kapanma nedeni yalnızca GİRVAK sayılarında. */
  durum: string;
  aranan: "genc" | "firma";
  aranan_firma_turleri: string[];
  isbirligi_turu: string | null;
};

/** POST /ihtiyac-kartlari/{id}/kapat — firma ilanını nedenle kapatır; tekrar 200. */
export function ihtiyacKartiKapat(
  kartId: string,
  neden: KapanmaNedeni,
): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>(`/ihtiyac-kartlari/${kartId}/kapat`, {
    method: "POST",
    body: JSON.stringify({ neden }),
  });
}

/** GET /ihtiyac-kartlari/{id} — firma kendi ilanını görür; başkasının 404. */
export function ihtiyacKarti(kartId: string): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>(`/ihtiyac-kartlari/${kartId}`);
}

/** PATCH /ihtiyac-kartlari/{id} — açık ilanı yerinde düzenler (docs/kararlar.md D1).
 *  Kapalı ya da iş birliği başlamış ilan 409 (cümle backend'den). Kapı değişmez. */
export function ihtiyacKartiDuzenle(
  kartId: string,
  taslak: IhtiyacTaslagi,
): Promise<IhtiyacKartiYaniti> {
  return apiIstek<IhtiyacKartiYaniti>(`/ihtiyac-kartlari/${kartId}`, {
    method: "PATCH",
    body: JSON.stringify(taslak),
  });
}

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
export function tanimlamaBaslat(
  aranan: "genc" | "firma" = "genc",
): Promise<TanimlamaSohbetYaniti> {
  return apiIstek<TanimlamaSohbetYaniti>("/tanimlama/sohbet/baslat", {
    method: "POST",
    body: JSON.stringify({ aranan }),
  });
}

/** POST /tanimlama/sohbet/cevap */
export type TanimlamaSohbetDurumu = TanimlamaSohbetYaniti & {
  mesajlar: { kim: "ajan" | "kullanici"; metin: string }[];
};

/** GET /tanimlama/sohbet/{id} — yenilenen sayfada sohbeti geri yükler; başkasının 404. */
export function tanimlamaSohbetDurumu(
  oturumId: string,
): Promise<TanimlamaSohbetDurumu> {
  return apiIstek<TanimlamaSohbetDurumu>(`/tanimlama/sohbet/${oturumId}`);
}

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
 *  (docs/agent-specs.md § 4) — arayüz de dördünü ayrı gösterir.
 *  null = "—": başlık değerlendirilmedi ya da yanıt yok (0 ile karıştırılmaz). */
export type GuvenSkoru = {
  kanit_orijinalligi: number | null;
  sonuc_olculebilirligi: number | null;
  rol_netligi: number | null;
  ucuncu_taraf_onayi: number | null;
  gerekce_metni: string | null;
};

/** Bir kanıt parçası. `erisim` ve `platform` kanıt okuyucusu gelince dolar. */
export type KanitParcasi = {
  id: string;
  /** "link" | "dosya" | "gorsel" */
  tur: string;
  url: string | null;
  platform?: string | null;
  erisim?: string | null;
  /** duzenleyen | platform | kamuya_acik | beyan */
  seviye?: string | null;
  /** Yüklenen dosyanın adı; firma, genç açmadıysa null görür. */
  dosya_adi?: string | null;
  dosya_boyutu?: number | null;
  gorunur_firmaya?: boolean;
  /** e-Devlet belgesi: bekliyor | onaylandi | reddedildi */
  girvak_incelemesi?: string | null;
  /** C2PA bilgisindeki üretim aracı */
  uretim_araci?: string | null;
};

/** Referans formunun (2)-(4). sorularına yanıt (dogrulama-iyilestirme § 7). */
export type FormCevabi = "evet" | "kismen" | "hayir" | "bilmiyorum";
/** Formun (1). sorusu: referans kişiyi nereden tanıyor. */
export type ReferansIliskisi =
  "yonetici" | "takim_arkadasi" | "ogretmen_danisman" | "musteri" | "diger";

/** Referans satırı. Token ve yanıt linki yok: e-posta referansa doğrudan gider. */
export type ReferansDurumu = {
  id: string;
  referans_email: string;
  /** "bekliyor" | "yanitlandi" | "yanit_yok" | "geri_cekildi" — yanıt geldi demek, olumlu demek değil. */
  durum: string;
  /** Eski formun 1-5 puanı; yeni yanıtlarda null. */
  puan: number | null;
  iliski: ReferansIliskisi | null;
  iddia_dogru: FormCevabi | null;
  pay_dogru: FormCevabi | null;
  sonuc_dogru: FormCevabi | null;
  yanit_metni: string | null;
  olusturma_tarihi: string;
  /** Güç işareti (puan değil). */
  guc: "kurumsal_eposta" | "egitim_eposta" | null;
  /** false: yanıt iş kaleminin önceki hâline verildi; güven göstergesine girmez. */
  guncel: boolean;
  /** "Yeniden iste" düğmesi; kural backend'de, arayüz tekrar etmez. */
  yeniden_istenebilir: boolean;
  /** "Geri çek" düğmesi (yalnızca bekleyen istek). */
  geri_cekilebilir: boolean;
};

export type KanitDurumu = {
  somut_cikti_id: string;
  baslik: string;
  kanitlar: KanitParcasi[];
  link_erisilebilir: boolean | null;
  guven_skoru: GuvenSkoru | null;
  referanslar: ReferansDurumu[];
  /** Kartın "Kanıt bekliyor" rozeti (sayfa yenilenmeden güncellenir). */
  kart_kanit_bekleyen: boolean;
  /** Gencin itirazı GİRVAK'ta bekliyor: hak doldu ya da karara itiraz (yanıt 202). */
  inceleme_bekliyor: boolean;
  /** GİRVAK'ın geçerli "doğrulanamadı" kararı (kalemin etiketi; puan değişmez). */
  dogrulanamadi: boolean;
  girvak_notlari: string[];
};

/** Referans kişinin yanıt vermeden önce gördüğü bilgi — iletişim bilgisi yok. */
export type ReferansIstegiBilgisi = {
  somut_cikti_id: string;
  baslik: string;
  aciklama: string | null;
  iddia_sahibi_adi: string;
  /** Formun (3) ve (4). sorusu bunları ayrı satırda gösterir; boşsa soru sorulmaz. */
  pay: string | null;
  sonuc: string | null;
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

const kalemYolu = (id: string) => `/dogrulama/kalem/${id}`;

/** GET /dogrulama/kalem/{id} — zaman aşımı bu okuma anında hesaplanır. */
export function kalemDurumu(somutCiktiId: string): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(kalemYolu(somutCiktiId), { cache: "no-store" });
}

/** POST /dogrulama/kalem/{id}/kanit — link ekler ve çalışmayı değerlendirir. */
export function kanitLinkiEkle(
  somutCiktiId: string,
  url: string,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/kanit`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/** POST /dogrulama/kalem/{id}/dosya — PDF ya da görsel yükler, çalışmayı değerlendirir. */
export function kanitDosyasiEkle(
  somutCiktiId: string,
  dosya: File,
): Promise<KanitDurumu> {
  const govde = new FormData();
  govde.append("dosya", dosya);
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/dosya`, {
    method: "POST",
    body: govde,
  });
}

/** GET /dogrulama/kalem/{id}/kanit/{parca}/indir — birkaç dakika geçerli indirme adresi. */
export function kanitDosyasiAdresi(
  somutCiktiId: string,
  parcaId: string,
): Promise<{ adres: string }> {
  return apiIstek<{ adres: string }>(
    `${kalemYolu(somutCiktiId)}/kanit/${parcaId}/indir`,
    { cache: "no-store" },
  );
}

/** PATCH /dogrulama/kalem/{id}/kanit/{parca} — "Firmalar görebilir". */
export function dosyaGorunurlugu(
  somutCiktiId: string,
  parcaId: string,
  gorunurFirmaya: boolean,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/kanit/${parcaId}`, {
    method: "PATCH",
    body: JSON.stringify({ gorunur_firmaya: gorunurFirmaya }),
  });
}

/** GET /yetenek-kartlari/{kart}/kanit/{parca}/indir — kart görünümünden indirme. */
export function kartDosyasiAdresi(
  kartId: string,
  parcaId: string,
): Promise<{ adres: string }> {
  return apiIstek<{ adres: string }>(
    `/yetenek-kartlari/${kartId}/kanit/${parcaId}/indir`,
    { cache: "no-store" },
  );
}

/** DELETE /dogrulama/kalem/{id}/kanit/{parca} — kanıtı kaldırır. */
export function kanitParcasiSil(
  somutCiktiId: string,
  parcaId: string,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/kanit/${parcaId}`, {
    method: "DELETE",
  });
}

/** POST /dogrulama/kalem/{id}/degerlendir — mevcut kanıtla değerlendirir. */
export function kalemiDegerlendir(somutCiktiId: string): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/degerlendir`, {
    method: "POST",
  });
}

/** POST /dogrulama/kalem/{id}/referans — referans ister; değerlendirme çalışmaz. */
export function referansIste(
  somutCiktiId: string,
  referansEmail: string,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/referans`, {
    method: "POST",
    body: JSON.stringify({ referans_email: referansEmail }),
  });
}

/** POST /dogrulama/referans/{id}/geri-cek — bekleyen isteği geri çeker; tekrarı yan etkisiz. */
export function referansGeriCek(referansId: string): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(
    `/dogrulama/referans/${encodeURIComponent(referansId)}/geri-cek`,
    { method: "POST" },
  );
}

/** POST /dogrulama/referans-yeniden-iste — aynı kişiye yeni istek; eski yanıt geçmişte kalır. */
export function referansYenidenIste(referansId: string): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>("/dogrulama/referans-yeniden-iste", {
    method: "POST",
    body: JSON.stringify({ referans_id: referansId }),
  });
}

/** POST /dogrulama/kalem/{id}/itiraz — değerlendirmeyi yeniden hesaplatır. */
export function itirazEt(
  somutCiktiId: string,
  aciklama: string,
): Promise<KanitDurumu> {
  return apiIstek<KanitDurumu>(`${kalemYolu(somutCiktiId)}/itiraz`, {
    method: "POST",
    body: JSON.stringify({ aciklama }),
  });
}

/** Referans yanıtından sonra dönen tek bilgi. Girişsiz uç nokta olduğu için
 *  diğer referansların e-postası, puanı ya da token'ı burada yok. */
export type ReferansYanitiSonucu = {
  baslik: string;
  durum: string;
};

/** Referans formunun gövdesi; kalemde yazılmamış pay / sonuç sorulmaz (null). */
export type ReferansFormu = {
  iliski: ReferansIliskisi;
  iddia_dogru: FormCevabi;
  pay_dogru: FormCevabi | null;
  sonuc_dogru: FormCevabi | null;
  yorum: string | null;
};

/** POST /dogrulama/referans-yaniti — girişsiz, token bazlı. */
export function referansYanitla(
  token: string,
  form: ReferansFormu,
): Promise<ReferansYanitiSonucu> {
  return apiIstek<ReferansYanitiSonucu>("/dogrulama/referans-yaniti", {
    method: "POST",
    body: JSON.stringify({ token, ...form }),
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
  /** Firma–firma yapay zekâ kararı; "kismen" ise rozet gösterilir. Genç ilanında null. */
  uygunluk: Uygunluk;
  /** Genç ilanında yetenek kartı, ortak ilanında firma kartı (tam biri dolu). */
  aday_turu: "genc" | "firma";
  yetenek_karti: YetenekKartiYaniti | null;
  firma_karti: FirmaAdayKarti | null;
  /** Yalnızca `kabul_edildi` durumunda ve yalnızca iki tarafa dolu. */
  iletisim: Iletisim | null;
  /** Genç ilgi gösterdi, firmanın yanıtı bekleniyor. Skoru değiştirmez. */
  genc_ilgi_gosterdi: boolean;
  /** Karşılıklı ilgiden sonra arayüz yerel olarak doldurur (iş birliği bağlantısı). */
  isbirligi_id?: string | null;
};

/** Gencin kabulüyle açılan e-postalar (docs/kimlik-ve-dongu.md § 5). */
export type Iletisim = {
  /** Genç ilanında gencin, ortak ilanında aday firmanın e-postası. */
  genc_email: string | null;
  aday_firma_email?: string | null;
  kurum_email: string | null;
};

/** Ortak ilanında önerilen firma (docs/kararlar.md F16-17). */
export type FirmaAdayKarti = {
  firma_karti_id: string;
  kurum_id: string;
  firma_adi: string;
  tur: FirmaTuru | null;
  sektor: string | null;
  sehir: string | null;
  dogrulandi: boolean;
  ne_yapiyoruz: string;
  yetkinlikler: string[];
  onceki_isler: string | null;
  isbirligi_turleri: string[];
  tamamlanan_isbirligi: number;
};

export type Oneriler = {
  ihtiyac_karti_id: string;
  oneriler: Oneri[];
  /** Havuz küçükken gizlenmez, açıkça söylenir (matching-algorithm.md § 5). */
  az_sonuc_uyarisi: boolean;
};

/** İlgileniyorum / kabul / red sonrası eşleşme. İş birliği gencin
 *  kabulüyle açılır; öncesinde `isbirligi_id` ve `iletisim` null. */
export type EslesmeDurumYaniti = {
  eslesme_id: string;
  durum: string;
  isbirligi_id: string | null;
  iletisim: Iletisim | null;
};

/** GET /eslestirme/oneriler/{kurum_id} — hesaplanmış listeyi okur.
 *  Kayıt varsa yeniden hesaplamaz; tazelemek için `eslestirmeCalistir`.
 *  `ihtiyacKartiId` verilmezse kurumun en son ihtiyaç kartı. */
export function eslestirmeOnerileri(
  kurumId: string,
  ihtiyacKartiId?: string | null,
): Promise<Oneriler> {
  const sorgu = ihtiyacKartiId
    ? `?ihtiyac_karti_id=${encodeURIComponent(ihtiyacKartiId)}`
    : "";
  return apiIstek<Oneriler>(`/eslestirme/oneriler/${kurumId}${sorgu}`, {
    cache: "no-store",
  });
}

/**
 * POST /eslestirme/calistir — pipeline'ı yeniden çalıştırır: skorlar tazelenir,
 * eksik gerekçeler üretilir, artık uygun olmayan öneriler listeden düşer.
 * Kurumun karar verdiği eşleşmelere dokunulmaz.
 */
export function eslestirmeCalistir(
  ihtiyacKartiId?: string | null,
): Promise<Oneriler> {
  // Kurum token'dan belli; gövdede kurum_id yalnızca GİRVAK için.
  return apiIstek<Oneriler>("/eslestirme/calistir", {
    method: "POST",
    body: JSON.stringify(
      ihtiyacKartiId ? { ihtiyac_karti_id: ihtiyacKartiId } : {},
    ),
  });
}

/** POST /eslestirme/ilgileniyorum — `onerildi` → `ilgileniliyor`. İş birliği
 *  açmaz; gencin kabulünü bekler. */
export function ilgileniyorum(eslesmeId: string): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>("/eslestirme/ilgileniyorum", {
    method: "POST",
    body: JSON.stringify({ eslesme_id: eslesmeId }),
  });
}

/* --- Gencin ana sayfası ve gençten ilgi (docs/api-contracts.md) ----- */

/** Fırsat ya da gencin kendi ilgisi. `uyum` 0-1 ("%72 uyum" olarak yazılır). */
export type GencEslesmesi = {
  eslesme_id: string;
  durum: string;
  uyum: number;
  /** "Neden uygun?" metni; firmaya yazılanın aynısı. Yoksa null. */
  gerekce_metni: string | null;
  son_aktivite_tarihi: string;
  yetenek_karti_id: string;
  rol_alani: string;
  ihtiyac_karti: IhtiyacKartiYaniti;
  isbirligi_id: string | null;
  /** Yalnızca karşılıklı ilgide dolu. */
  iletisim: Iletisim | null;
};

/** "Kartını güçlendir" satırı. Sayı gerçek skorlardan; metin şablon. */
export type Guclendirme = {
  somut_cikti_id: string;
  baslik: string;
  one_cikacagi_firsat: number;
  metin: string;
};

/** GET /eslestirme/firsatlarim — "Sana uygun fırsatlar". */
export function firsatlarim(): Promise<GencEslesmesi[]> {
  return apiIstek<GencEslesmesi[]>("/eslestirme/firsatlarim");
}

/** GET /eslestirme/ilgilerim — gencin kendi gösterdiği ilgiler. */
export function ilgilerim(): Promise<GencEslesmesi[]> {
  return apiIstek<GencEslesmesi[]>("/eslestirme/ilgilerim");
}

/** GET /yetenek-kartlari/{id}/guclendir */
export function kartGuclendir(kartId: string): Promise<Guclendirme[]> {
  return apiIstek<Guclendirme[]>(`/yetenek-kartlari/${kartId}/guclendir`);
}

/** POST /eslestirme/{id}/genc-ilgi — iletişim onayı zorunlu. */
export function gencIlgi(eslesmeId: string): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>(`/eslestirme/${eslesmeId}/genc-ilgi`, {
    method: "POST",
    body: JSON.stringify({ iletisim_onayi: true }),
  });
}

/* --- Firmalar arası ilgi: aday firmanın tarafı (docs/kararlar.md F8) --- */

/** `GET /eslestirme/firma-eslesmelerim` satırı. `baslatan`: "genc" = aday tarafı. */
export type FirmaAdayEslesmesi = {
  eslesme_id: string;
  durum: string;
  uyum: number;
  gerekce_metni: string | null;
  /** Yapay zekâ kararı; "kismen" ise rozet gösterilir. */
  uygunluk: Uygunluk;
  son_aktivite_tarihi: string;
  baslatan: string | null;
  ihtiyac_karti: IhtiyacKartiYaniti;
  isbirligi_id: string | null;
  iletisim: Iletisim | null;
};

export function firmaEslesmelerim(): Promise<FirmaAdayEslesmesi[]> {
  return apiIstek<FirmaAdayEslesmesi[]>("/eslestirme/firma-eslesmelerim", {
    cache: "no-store",
  });
}

function firmaGecisi(eslesmeId: string, yol: string, govde?: object) {
  return apiIstek<EslesmeDurumYaniti>(`/eslestirme/${eslesmeId}/${yol}`, {
    method: "POST",
    ...(govde ? { body: JSON.stringify(govde) } : {}),
  });
}

/** Aday firma ilgi gösterir; açık iletişim onayıyla. */
export const firmaIlgi = (eslesmeId: string) =>
  firmaGecisi(eslesmeId, "firma-ilgi", { iletisim_onayi: true });
export const firmaIlgiyiGeriCek = (eslesmeId: string) =>
  firmaGecisi(eslesmeId, "firma-ilgiyi-geri-cek");
export const firmaKabul = (eslesmeId: string) =>
  firmaGecisi(eslesmeId, "firma-kabul");
export const firmaRed = (eslesmeId: string) =>
  firmaGecisi(eslesmeId, "firma-red");

/** POST /eslestirme/{id}/ilgiyi-geri-cek — karşılıklı hâle gelmeden önce. */
export function ilgiyiGeriCek(eslesmeId: string): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>(
    `/eslestirme/${eslesmeId}/ilgiyi-geri-cek`,
    { method: "POST" },
  );
}

/** POST /eslestirme/{id}/simdilik-degil — firma, ilgi gösteren gence. */
export function simdilikDegil(eslesmeId: string): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>(
    `/eslestirme/${eslesmeId}/simdilik-degil`,
    { method: "POST" },
  );
}

/* --- Paneller (docs/kimlik-ve-dongu.md § 5, § 7) -------------------- */

/** Gencin kartına gelen ilgi: kurum "ilgileniyorum" dedikten sonra görünür. */
export type BanaGelenIlgi = {
  eslesme_id: string;
  /** "ilgileniliyor" | "kabul_edildi" | "reddedildi" */
  durum: string;
  son_aktivite_tarihi: string;
  yetenek_karti_id: string;
  rol_alani: string;
  ihtiyac_karti: IhtiyacKartiYaniti;
  isbirligi_id: string | null;
  iletisim: Iletisim | null;
};

export function banaGelenler(): Promise<BanaGelenIlgi[]> {
  return apiIstek<BanaGelenIlgi[]>("/eslestirme/bana-gelenler", {
    cache: "no-store",
  });
}

/** POST /eslestirme/{id}/kabul — iş birliği açılır, e-postalar iki tarafa görünür. */
export function eslesmeyiKabulEt(
  eslesmeId: string,
): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>(`/eslestirme/${eslesmeId}/kabul`, {
    method: "POST",
  });
}

export function eslesmeyiReddet(
  eslesmeId: string,
): Promise<EslesmeDurumYaniti> {
  return apiIstek<EslesmeDurumYaniti>(`/eslestirme/${eslesmeId}/red`, {
    method: "POST",
  });
}

/** Kurum panelindeki öneri özeti (tüm ihtiyaç kartlarından). */
export type KurumOnerisi = {
  eslesme_id: string;
  durum: string;
  skor: number;
  son_aktivite_tarihi: string;
  ihtiyac_karti_id: string;
  problem_tanimi: string;
  /** E-posta taslağı için; e-posta adresi değil. */
  basari_kriteri: string | null;
  calisma_basligi: string | null;
  aday_turu: "genc" | "firma";
  aday_adi: string;
  yetenek_karti_id: string | null;
  firma_karti_id: string | null;
  /** Yalnızca genç adayında. */
  genc_adi: string | null;
  rol_alani: string | null;
  iletisim: Iletisim | null;
};

export function onerilerim(): Promise<KurumOnerisi[]> {
  return apiIstek<KurumOnerisi[]>("/eslestirme/onerilerim", {
    cache: "no-store",
  });
}

/** `GET /isbirliklerim` satırı — iki tarafa aynı görünüm, e-postalar dahil. */
export type IsbirligiOzeti = {
  isbirligi_id: string;
  durum: string;
  baslangic_tarihi: string | null;
  eslesme_id: string;
  /** Aday tarafı: genç ya da ortak firma (docs/takip.md (Ek)). */
  aday_turu: "genc" | "firma";
  aday_adi: string;
  /** Yalnızca genç adayında. */
  genc_adi: string | null;
  kurum_adi: string;
  rol_alani: string | null;
  /** İsteyenin tarafı (genc = aday, kurum = ilan); karşı tarafı seçmek için. */
  tarafim: "genc" | "kurum" | null;
  problem_tanimi: string;
  basari_kriteri: string | null;
  calisma_basligi: string | null;
  iletisim: Iletisim;
  ilerleme: Ilerleme;
  /** İsteyen taraf planın mevcut hâlini onayladı (plan iki onayla aktif olur). */
  planimi_onayladim?: boolean;
};

export function isbirliklerim(): Promise<IsbirligiOzeti[]> {
  return apiIstek<IsbirligiOzeti[]>("/isbirliklerim", { cache: "no-store" });
}

export type GirvakSayilari = {
  hesap: { genc: number; kurum: number; girvak: number };
  yetenek_karti: number;
  ihtiyac_karti: number;
  eslesme: {
    onerildi: number;
    ilgileniliyor: number;
    kabul_edildi: number;
    reddedildi: number;
  };
  isbirligi: number;
  /** `tamamlandi` = tamamlanmış iş birliği (program hedefi: 5). */
  isbirligi_durumlari: {
    plan_bekliyor: number;
    aktif: number;
    tamamlandi: number;
  };
  /** Programın adı + platformda ne sayıldığı (fark gizlenmez). */
  hedefler: ProgramHedefi[];
  /** Firma akışı: kapanan ilanlar, firmanın seçtiği nedene göre. */
  kapanan_ihtiyaclar: {
    platformda_bulundu: number;
    baska_yoldan_bulundu: number;
    vazgecildi: number;
    hatali_girildi: number;
    nedensiz: number;
  };
  /** Toplamların eşleşme türüne göre kırılımı (docs/kararlar.md F19). */
  kirilim: { genc_firma: TurSayilari; firma_firma: TurSayilari };
};

export type TurSayilari = {
  oneri: number;
  karsilikli_ilgi: number;
  isbirligi: number;
  tamamlanan: number;
};

export type ProgramHedefi = {
  anahtar: "basvuru" | "kurum" | "eslesme" | "pilot";
  program_adi: string;
  olcum: string;
  sayi: number;
  hedef: number;
};

/** GİRVAK'ın firma doğrulama listesi (docs/kararlar.md F6). */
/* --- GİRVAK inceleme kuyruğu (docs/dogrulama.md § 9) ---- */

export type IncelemeDurumu = "acik" | "kapandi" | "dogrulanamadi";

export type IncelemeSatiri = {
  id: string;
  tur: string;
  durum: IncelemeDurumu;
  olusturma_tarihi: string;
  kapanma_tarihi: string | null;
  girvak_notu: string | null;
  genc_adi: string | null;
  kart_id: string | null;
  somut_cikti_id: string | null;
  cikti_basligi: string | null;
  /** Türe özel bağlam (lib/inceleme.ts okur). */
  ayrinti: Record<string, unknown>;
};

export function girvakIncelemeler(
  durum: IncelemeDurumu = "acik",
): Promise<IncelemeSatiri[]> {
  return apiIstek(`/girvak/inceleme?durum=${durum}`);
}

export function girvakIncelemeKarari(
  id: string,
  karar: "kapandi" | "dogrulanamadi",
  girvakNotu: string | null,
): Promise<IncelemeSatiri> {
  return apiIstek(`/girvak/inceleme/${id}/karar`, {
    method: "POST",
    body: JSON.stringify({ karar, girvak_notu: girvakNotu }),
  });
}

export type OnayBekleyenFirma = {
  kurum_id: string;
  ad: string;
  tur: FirmaTuru | null;
  sektor: string | null;
  sehir: string | null;
  web_sitesi: string | null;
  /** Tam e-posta değil, yalnızca uzantısı. */
  eposta_alan_adi: string | null;
  ipucu: AlanAdiIpucu;
  dogrulama_durumu: "bekliyor" | "dogrulandi" | "simdilik_degil";
  dogrulama_tarihi: string | null;
  kayit_tarihi: string;
};

/** GET /girvak/firmalar — varsayılan: onay bekleyenler. */
export function girvakFirmalar(
  durum: "bekliyor" | "dogrulandi" | "simdilik_degil" = "bekliyor",
): Promise<OnayBekleyenFirma[]> {
  return apiIstek<OnayBekleyenFirma[]>(`/girvak/firmalar?durum=${durum}`, {
    cache: "no-store",
  });
}

/** POST /girvak/firmalar/{id}/dogrula — tekrar 200, yan etkisiz. */
export function girvakFirmaDogrula(
  kurumId: string,
  karar: "dogrulandi" | "simdilik_degil",
): Promise<OnayBekleyenFirma> {
  return apiIstek<OnayBekleyenFirma>(`/girvak/firmalar/${kurumId}/dogrula`, {
    method: "POST",
    body: JSON.stringify({ karar }),
  });
}

export function girvakSayilari(): Promise<GirvakSayilari> {
  return apiIstek<GirvakSayilari>("/girvak/sayilar", { cache: "no-store" });
}

/* --- GİRVAK gözlem paneli (docs/dogrulama.md § 10.3) -------
   Tipler backend'deki app/schemas/gozlem.py ile birebir eşleşir. */

export type PlatformErisimi = {
  platform: string;
  toplam: number;
  /** erişim durumu → okuma sayısı */
  erisimler: Record<string, number>;
  /** 0-1 */
  acik_orani: number;
};

export type ServisDurumu = {
  servis: string;
  kip: string | null;
  basari_sayisi: number;
  hata_sayisi: number;
  son_basari: string | null;
  son_hata: string | null;
  son_hata_turu: string | null;
};

export type GozlemYaniti = {
  gun: number;
  erisim: PlatformErisimi[];
  servisler: ServisDurumu[];
  degerlendirme: {
    sayi: number;
    ortalama_sure_ms: number;
    girdi_token: number;
    cikti_token: number;
  };
};

export function girvakGozlem(gun: number): Promise<GozlemYaniti> {
  return apiIstek<GozlemYaniti>(`/girvak/gozlem?gun=${gun}`, {
    cache: "no-store",
  });
}

/* --- Takip Ajanı (docs/takip.md § 7) --------------------------------
   Tipler backend'deki app/schemas/takip.py ile birebir eşleşir. */

export type Ilerleme = { tamamlanan: number; toplam: number; geciken: number };

export type MilestoneYaniti = {
  id: string;
  sira: number;
  baslik: string;
  aciklama: string | null;
  /** Hazırlık önerisi (süreç şablonundan ya da kişiselleştirilmiş). */
  oneri?: string | null;
  hedef_tarih: string | null;
  /** "bekliyor" | "tamamlandi" */
  durum: string;
  genc_isaret: string | null;
  kurum_isaret: string | null;
  kanit_linki: string | null;
  /** Okuma anında hesaplanır: hedef tarih geçti, adım tamamlanmadı. */
  gecikmis: boolean;
};

/** "plan_bekliyor" | "aktif" | "tamamlandi" */
export type IsbirligiDurumu =
  "plan_bekliyor" | "aktif" | "tamamlandi" | "sonlandi";

/** Süreci sonlandırma nedeni: yalnızca kayıtta, karşı tarafa gösterilmez. */
export type SonlanmaNedeni =
  "karar_olumsuz" | "baska_yoldan_ilerlendi" | "iletisim_kurulamadi";

export type IsbirligiDetayi = {
  id: string;
  durum: IsbirligiDurumu;
  /** Süreç şablonu ve görünen adı ("İşe alım süreci"); eski kayıtta null. */
  surec?: string | null;
  surec_adi?: string | null;
  baslangic_tarihi: string | null;
  tamamlanma_tarihi: string | null;
  eslesme_id: string;
  ihtiyac_karti_id: string;
  /** Aday tarafı: genç ya da ortak firma (docs/takip.md (Ek)). */
  aday_turu: "genc" | "firma";
  aday_adi: string;
  yetenek_karti_id: string | null;
  firma_karti_id: string | null;
  /** Yalnızca genç adayında. */
  genc_adi: string | null;
  kurum_adi: string;
  rol_alani: string | null;
  /** İsteyenin eşleşmedeki tarafı; ortak firmanın rolü de "kurum" olduğu için
   *  arayüz tarafı rolden değil buradan okur. GİRVAK'ta null. */
  tarafim: "genc" | "kurum" | null;
  problem_tanimi: string;
  basari_kriteri: string | null;
  calisma_basligi: string | null;
  genc_plan_onayi: string | null;
  kurum_plan_onayi: string | null;
  plan_onerildi_mi: boolean;
  milestonelar: MilestoneYaniti[];
  ilerleme: Ilerleme;
  durum_ozeti: string | null;
  ozet_tarihi: string | null;
  /** İki tarafa dolu, GİRVAK'a null. */
  iletisim: Iletisim | null;
};

export type MilestoneGirdisi = {
  baslik?: string;
  aciklama?: string | null;
  hedef_tarih?: string | null;
  kanit_linki?: string | null;
};

const isbirligiYolu = (id: string) => `/isbirligi/${id}`;

export function isbirligiGetir(id: string): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(isbirligiYolu(id), { cache: "no-store" });
}

/** Ajandan (yeniden) plan ister; mevcut adımları siler, iki onayı sıfırlar. */
export function planOner(id: string): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(`${isbirligiYolu(id)}/plan-oner`, {
    method: "POST",
  });
}

export function milestoneEkle(
  id: string,
  girdi: MilestoneGirdisi & { baslik: string },
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(`${isbirligiYolu(id)}/milestone-ekle`, {
    method: "POST",
    body: JSON.stringify(girdi),
  });
}

/** Yalnızca gönderilen alanlar değişir (PATCH). */
export function milestoneGuncelle(
  id: string,
  milestoneId: string,
  girdi: MilestoneGirdisi,
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(
    `${isbirligiYolu(id)}/milestone/${milestoneId}`,
    { method: "PATCH", body: JSON.stringify(girdi) },
  );
}

export function milestoneSil(
  id: string,
  milestoneId: string,
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(
    `${isbirligiYolu(id)}/milestone/${milestoneId}`,
    { method: "DELETE" },
  );
}

export function planOnayla(id: string): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(`${isbirligiYolu(id)}/plan-onayla`, {
    method: "POST",
  });
}

/** POST /isbirligi/{id}/sonlandir — bir taraf süreci sonlandırır; tekrar 200. */
export function isbirligiSonlandir(
  id: string,
  neden: SonlanmaNedeni,
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(`${isbirligiYolu(id)}/sonlandir`, {
    method: "POST",
    body: JSON.stringify({ neden }),
  });
}

export function milestoneIsaretle(
  id: string,
  milestoneId: string,
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(
    `${isbirligiYolu(id)}/milestone/${milestoneId}/isaretle`,
    { method: "POST" },
  );
}

export function milestoneIsaretiGeriAl(
  id: string,
  milestoneId: string,
): Promise<IsbirligiDetayi> {
  return apiIstek<IsbirligiDetayi>(
    `${isbirligiYolu(id)}/milestone/${milestoneId}/isareti-geri-al`,
    { method: "POST" },
  );
}

/* --- Canlılık (docs/canlilik.md § 8) — yalnızca GİRVAK ---------------- */

export type TaramaSonucu = {
  tarih: string;
  /** tür → yazılan olay sayısı */
  olaylar: Record<string, number>;
  bildirim: number;
  sure_sn: number;
};

export type PasifBaglanti = {
  tur: string;
  eslesme_id: string;
  isbirligi_id: string | null;
  genc_adi: string;
  kurum_adi: string;
  gun: number;
  adim: string | null;
  alicilar: string[];
  son_hatirlatma: string | null;
};

export type CanlilikOlayi = {
  id: string;
  tur: string;
  mesaj_metni: string | null;
  tetiklenme_tarihi: string;
  alici_adi: string | null;
  alici_rol: Rol | null;
  eslesme_id: string;
};

/** POST /canlilik/tarama — "Taramayı şimdi çalıştır". İdempotent. */
export function taramaCalistir(): Promise<TaramaSonucu> {
  return apiIstek<TaramaSonucu>("/canlilik/tarama", { method: "POST" });
}

export function pasifBaglantilar(): Promise<PasifBaglanti[]> {
  return apiIstek<PasifBaglanti[]>("/canlilik/pasifler", { cache: "no-store" });
}

export function canlilikOlaylari(limit = 20): Promise<CanlilikOlayi[]> {
  return apiIstek<CanlilikOlayi[]>(`/canlilik/olaylar?limit=${limit}`, {
    cache: "no-store",
  });
}

export { API_URL };

/* --- Hesap bağlama (docs/dogrulama.md § 6) ------------------
   Tipler backend'deki app/schemas/hesap_baglama.py ile eşleşir. */

export type BagliHesap = {
  id: string;
  saglayici: string;
  kullanici_adi: string;
  /** oauth | profil_kodu | elle (GİRVAK'ın doğruladığı kod) */
  yontem: string;
  baglanma_tarihi: string;
};

export type ProfilKodu = {
  platform: string;
  kod: string;
  /** Kodun aranacağı profil adresi (sunucu kurar). */
  profil_adresi: string;
  son_gecerlilik: string;
};

export type Hesaplarim = {
  hesaplar: BagliHesap[];
  oauth_saglayicilari: string[];
  profil_kodu_platformlari: string[];
  bekleyen_kodlar: ProfilKodu[];
  /** GİRVAK'ın elle doğrulamasını bekleyen platform. */
  inceleme_bekleyen: string | null;
};

export type KodDogrulamaYaniti = {
  durum: "baglandi" | "inceleme_bekliyor";
  hesap: BagliHesap | null;
};

/** GET /hesap-baglama — bağlı hesaplar, açık yöntemler, bekleyen kodlar. */
export function hesaplarim(): Promise<Hesaplarim> {
  return apiIstek<Hesaplarim>("/hesap-baglama");
}

/** POST /hesap-baglama/oauth/{saglayici}/baslat — yönlendirilecek yetki adresi. */
export function oauthBaslat(
  saglayici: string,
): Promise<{ yetki_adresi: string }> {
  return apiIstek<{ yetki_adresi: string }>(
    `/hesap-baglama/oauth/${saglayici}/baslat`,
    { method: "POST" },
  );
}

/** POST /hesap-baglama/oauth/{saglayici}/tamamla — sağlayıcıdan dönen kodla bağlar. */
export function oauthTamamla(
  saglayici: string,
  kod: string,
  durum: string,
): Promise<BagliHesap> {
  return apiIstek<BagliHesap>(`/hesap-baglama/oauth/${saglayici}/tamamla`, {
    method: "POST",
    body: JSON.stringify({ kod, durum }),
  });
}

/** POST /hesap-baglama/profil-kodu — 48 saatlik doğrulama kodu. */
export function profilKoduAl(
  platform: string,
  profilAdresi: string,
): Promise<ProfilKodu> {
  return apiIstek<ProfilKodu>("/hesap-baglama/profil-kodu", {
    method: "POST",
    body: JSON.stringify({ platform, profil_adresi: profilAdresi }),
  });
}

/** POST /hesap-baglama/profil-kodu/{platform}/dogrula — profili okur. */
export function profilKodunuDogrula(
  platform: string,
): Promise<KodDogrulamaYaniti> {
  return apiIstek<KodDogrulamaYaniti>(
    `/hesap-baglama/profil-kodu/${platform}/dogrula`,
    { method: "POST" },
  );
}

/** DELETE /hesap-baglama/{id} — güncel listeyi döner. */
export function baglantiyiKaldir(id: string): Promise<Hesaplarim> {
  return apiIstek<Hesaplarim>(`/hesap-baglama/${id}`, { method: "DELETE" });
}
