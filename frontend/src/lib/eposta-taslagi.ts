/**
 * "E-posta yaz" düğmesinin taslağı (docs/api-contracts.md, "Eşleşmeden sonra e-posta").
 *
 * Şablon, LLM yok. Metinler docs/icerik-rehberi.md'ye uyar: gence "sen",
 * firmaya "siz". `mailto:` bağlantısı uzun olursa bazı e-posta programları
 * keser; bu yüzden kodlanmış bağlantı `MAILTO_SINIRI` karakteri geçmez,
 * sığmazsa önce çalışma cümlesi, sonra başarı ölçütü düşer, en sonda
 * problem metni kısalır.
 */

export const MAILTO_SINIRI = 1500;

/** Kimin kime yazdığı. `ilan` = ilanı açan firma, `aday` = önerilen genç ya da firma. */
export type TaslakYonu =
  "ilan-genc" | "genc-ilan" | "ilan-firma" | "firma-ilan";

export type TaslakGirdisi = {
  yon: TaslakYonu;
  /** E-postayı gönderenin adı (genç adı ya da firma adı). */
  gonderenAdi: string;
  /** Alıcının adı (genç adı ya da firma adı). */
  aliciAdi: string;
  problem: string;
  basariKriteri?: string | null;
  /** Genç adayın kartından bir çalışma başlığı; firma adayında yok. */
  calisma?: string | null;
};

/** Ekranın bildiği bağlam; yön `karsiTaraf` ve `adayTuru`'ndan çıkar. */
export type EpostaBaglami = Omit<TaslakGirdisi, "yon"> & {
  adayTuru: "genc" | "firma";
};

/**
 * `href`: mailto bağlantısı (bilgisayarın e-posta ayarına bağlı).
 * `gmailHref`: Gmail'de dolu bir yazma penceresi açar, ayara bağlı değil.
 */
export type EpostaTaslagi = {
  konu: string;
  govde: string;
  href: string;
  gmailHref: string;
};

type Secenek = { calisma: boolean; kriter: boolean; problemSiniri: number };

// Sığmadıkça sırayla vazgeçilenler.
const SECENEKLER: Secenek[] = [
  { calisma: true, kriter: true, problemSiniri: 160 },
  { calisma: false, kriter: true, problemSiniri: 160 },
  { calisma: false, kriter: false, problemSiniri: 160 },
  { calisma: false, kriter: false, problemSiniri: 100 },
  { calisma: false, kriter: false, problemSiniri: 60 },
  { calisma: false, kriter: false, problemSiniri: 30 },
];

const KONU_PROBLEM_SINIRI = 60;

/** Tek satıra indirir, sınırı aşarsa kelime sınırında keser ve "…" ekler. */
export function kisalt(metin: string, sinir: number): string {
  const duz = metin.replace(/\s+/g, " ").trim();
  if (duz.length <= sinir) return duz;
  const kesik = duz.slice(0, sinir - 1);
  const bosluk = kesik.lastIndexOf(" ");
  const govde = bosluk > sinir * 0.5 ? kesik.slice(0, bosluk) : kesik;
  return `${govde.replace(/[\s.,;:]+$/, "")}…`;
}

/** Cümle sonu noktası ve boşluk atılır; metin cümle içinde kullanılacak. */
function ozet(metin: string | null | undefined): string {
  return (metin ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[.\s]+$/, "");
}

function govdeKur(girdi: TaslakGirdisi, secenek: Secenek): string {
  const problem = kisalt(girdi.problem, secenek.problemSiniri);
  const kriter = secenek.kriter ? ozet(girdi.basariKriteri) : "";
  const calisma = secenek.calisma ? ozet(girdi.calisma) : "";
  const { gonderenAdi, aliciAdi } = girdi;

  switch (girdi.yon) {
    case "ilan-genc":
      return [
        `Merhaba ${aliciAdi},`,
        [
          `${gonderenAdi} olarak Zemin360'ta “${problem}” ihtiyacımız için eşleştik.`,
          calisma ? `Kartındaki “${calisma}” çalışman dikkatimizi çekti.` : "",
          kriter ? `Hedefimiz: ${kriter}.` : "",
        ]
          .filter(Boolean)
          .join(" "),
        "Bu hafta kısa bir tanışma görüşmesi yapabilir miyiz? Sana uygun gün ve saatleri yazarsan ayarlarız.",
        gonderenAdi,
      ].join("\r\n\r\n");
    case "genc-ilan":
      return [
        "Merhaba,",
        [
          `Ben ${gonderenAdi}. Zemin360'ta “${problem}” ihtiyacınız için eşleştik.`,
          calisma
            ? `“${calisma}” çalışmamın bu ihtiyaca yakın olduğunu düşünüyorum.`
            : "",
          kriter
            ? `${kriter} hedefinize nasıl katkı verebileceğimi konuşmak isterim.`
            : "Nasıl katkı verebileceğimi konuşmak isterim.",
        ]
          .filter(Boolean)
          .join(" "),
        "Size uygun bir zamanda kısa bir görüşme yapabilir miyiz?",
        gonderenAdi,
      ].join("\r\n\r\n");
    case "ilan-firma":
      return [
        "Merhaba,",
        [
          `${gonderenAdi} olarak Zemin360'ta “${problem}” ihtiyacımız için sizinle eşleştik.`,
          `${aliciAdi} olarak yaptıklarınız ihtiyacımızla örtüşüyor.`,
          kriter ? `Hedefimiz: ${kriter}.` : "",
        ]
          .filter(Boolean)
          .join(" "),
        "İş birliği için kısa bir tanışma görüşmesi yapabilir miyiz?",
        gonderenAdi,
      ].join("\r\n\r\n");
    case "firma-ilan":
      return [
        "Merhaba,",
        [
          `${gonderenAdi} olarak Zemin360'ta “${problem}” ihtiyacınız için sizinle eşleştik.`,
          "Yaptıklarımızın bu ihtiyaçla örtüştüğünü düşünüyoruz.",
          kriter
            ? `${kriter} hedefinize nasıl katkı verebileceğimizi konuşmak isteriz.`
            : "",
        ]
          .filter(Boolean)
          .join(" "),
        "İş birliği için kısa bir görüşme yapabilir miyiz?",
        gonderenAdi,
      ].join("\r\n\r\n");
  }
}

function konuKur(girdi: TaslakGirdisi): string {
  const kisa = kisalt(girdi.problem, KONU_PROBLEM_SINIRI);
  switch (girdi.yon) {
    case "ilan-genc":
      return `Zemin360: “${kisa}” için tanışalım`;
    case "genc-ilan":
    case "firma-ilan":
      return `Zemin360: “${kisa}” ihtiyacınız hakkında`;
    case "ilan-firma":
      return `Zemin360 eşleşmemiz: “${kisa}”`;
  }
}

/** Gmail'de alıcı, konu ve metni dolu bir yazma penceresi açan adres. */
export function gmailAdresi(
  aliciEposta: string,
  konu: string,
  govde: string,
): string {
  return `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(aliciEposta)}&su=${encodeURIComponent(konu)}&body=${encodeURIComponent(govde)}`;
}

/**
 * `mailto:` taslağı. Alıcı adresi çağıranın elindeki, yetkiyle açılmış
 * `iletisim` alanından gelir; bu fonksiyon adres üretmez ya da saklamaz.
 */
export function epostaTaslagi(
  girdi: TaslakGirdisi,
  aliciEposta: string,
): EpostaTaslagi {
  const konu = konuKur(girdi);
  let sonuc: EpostaTaslagi | null = null;
  for (const secenek of SECENEKLER) {
    const govde = govdeKur(girdi, secenek);
    const href = `mailto:${aliciEposta}?subject=${encodeURIComponent(konu)}&body=${encodeURIComponent(govde)}`;
    sonuc = {
      konu,
      govde,
      href,
      gmailHref: gmailAdresi(aliciEposta, konu, govde),
    };
    if (href.length <= MAILTO_SINIRI) break;
  }
  // SECENEKLER boş değil; son seçenek de sığmazsa en kısa hâliyle döner.
  return sonuc as EpostaTaslagi;
}

/** Gönderenin tarafından yön: `karsiTaraf` "kurum" ise gönderen aday tarafıdır. */
export function taslakYonu(
  karsiTaraf: "genc" | "kurum",
  adayTuru: "genc" | "firma",
): TaslakYonu {
  if (karsiTaraf === "genc")
    return adayTuru === "firma" ? "ilan-firma" : "ilan-genc";
  return adayTuru === "firma" ? "firma-ilan" : "genc-ilan";
}
