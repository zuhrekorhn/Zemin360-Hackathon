"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { OnayAlani } from "@/components/onay-alani";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type KanitDurumu,
  type KanitParcasi,
  type ReferansDurumu,
  dosyaGorunurlugu,
  itirazEt,
  kalemiDegerlendir,
  kanitDosyasiAdresi,
  kanitDosyasiEkle,
  kanitLinkiEkle,
  kanitParcasiSil,
  referansGeriCek,
  referansIste,
  referansYenidenIste,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  KABUL_EDILEN_DOSYALAR,
  type SecenekKutusu as SecenekKutusuVerisi,
  degerlendirildiMi,
  dosyaBoyutu,
  dosyaParcalari,
  girvakIncelemesiMetni,
  kanitAdresi,
  kanitLinkleri,
  okunamayanSecenekleri,
} from "@/lib/kanit";
import { notuBasliklaraAyir } from "@/lib/guven-gostergesi";
import { referansSatiri } from "@/lib/kart-duzenleme";
import { REFERANS_DURUMLARI, referansOzeti } from "@/lib/referans";

/**
 * Bir çalışmanın kanıt bölümü (docs/dogrulama.md § 3).
 *
 * Dört iş, dört ayrı eylem:
 *   - Kanıtlar: link, PDF ya da görsel eklenir (çalışma hemen değerlendirilir)
 *     ya da kaldırılır. Kanıt yalnızca buradan değişir; iddia düzenleme formu
 *     linke dokunmaz. Okunamayan linkin altında seçenek kutusu (§ 3); dosyayı
 *     varsayılan olarak yalnızca genç ve GİRVAK görür, genç firmalara açabilir.
 *   - Değerlendirme: linki olup henüz değerlendirilmemiş çalışma için.
 *   - Referans: istemek değerlendirmeyi yeniden çalıştırmaz. E-postayı sistem
 *     gönderir; yanıt linki gence gösterilmez (docs/dogrulama.md § 7). Yanlış
 *     adrese giden bekleyen istek geri çekilebilir.
 *   - İtiraz: değerlendirmeyi eksik bulan genç yeniden baktırır.
 */

/** Kanıt bölümünde açılabilecek ekleme formu; aynı anda yalnızca biri açık. */
export type EklemeFormu = "link" | "dosya" | "referans";

const EKLEME_DUGMELERI: { form: EklemeFormu; etiket: string }[] = [
  { form: "link", etiket: "Link" },
  { form: "dosya", etiket: "PDF ya da görsel" },
  { form: "referans", etiket: "Referans iste" },
];

export function KanitBolumu({
  somutCiktiId,
  kanitlar,
  durum,
  onDurum,
  onHata,
  acikForm,
  onAcikForm,
}: {
  somutCiktiId: string;
  /** Kart görünümündeki kanıtlar: kanıt durumu gelmeden de liste çizilsin. */
  kanitlar: KanitParcasi[];
  durum: KanitDurumu | undefined;
  onDurum: (durum: KanitDurumu) => void;
  onHata: (hata: Hata | null) => void;
  /** Açık ekleme formu; çalışma kartının "sıradaki adım" düğmesi de açar. */
  acikForm: EklemeFormu | null;
  onAcikForm: (form: EklemeFormu | null) => void;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const parcalar = durum?.kanitlar ?? kanitlar;
  const linkler = kanitLinkleri(parcalar);
  const dosyalar = dosyaParcalari(parcalar);
  const kanitVar = linkler.length + dosyalar.length > 0;
  const referanslar = durum?.referanslar ?? [];
  const degerlendirildi = degerlendirildiMi(durum?.guven_skoru);

  /** Bir eylemi çalıştırır; başarılıysa true (formlar kendini temizlesin diye). */
  async function calistir(is: () => Promise<KanitDurumu>): Promise<boolean> {
    onHata(null);
    setBekleniyor(true);
    try {
      onDurum(await is());
      return true;
    } catch (sebep) {
      onHata(hatayaCevir(sebep));
      return false;
    } finally {
      setBekleniyor(false);
    }
  }

  /** Ekleme başarılıysa form kapanır. */
  const ekle = (is: () => Promise<KanitDurumu>) =>
    calistir(is).then((tamam) => {
      if (tamam) onAcikForm(null);
      return tamam;
    });

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-2.5">
        <h4 className="text-sm font-semibold text-ana">Kanıtlar</h4>
        {kanitVar ? (
          <ul className="flex flex-col gap-3">
            {linkler.map((parca) => (
              <KanitSatiri
                key={parca.id}
                parca={parca}
                bekleniyor={bekleniyor}
                onKaldir={() =>
                  calistir(() => kanitParcasiSil(somutCiktiId, parca.id))
                }
              />
            ))}
            {dosyalar.map((parca) => (
              <DosyaSatiri
                key={parca.id}
                parca={parca}
                bekleniyor={bekleniyor}
                onIndir={() => indir(somutCiktiId, parca.id, onHata)}
                onGorunurluk={(gorunur) =>
                  calistir(() =>
                    dosyaGorunurlugu(somutCiktiId, parca.id, gorunur),
                  )
                }
                onKaldir={() =>
                  calistir(() => kanitParcasiSil(somutCiktiId, parca.id))
                }
              />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Henüz kanıt eklemedin.
          </p>
        )}
        {kanitVar && durum && !degerlendirildi ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              size="sm"
              disabled={bekleniyor}
              onClick={() =>
                void calistir(() => kalemiDegerlendir(somutCiktiId))
              }
            >
              {bekleniyor ? "Değerlendiriliyor…" : "Bu kanıtı değerlendir"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Bu kanıt henüz değerlendirilmedi.
            </span>
          </div>
        ) : null}
      </section>

      {referanslar.length > 0 ? (
        <section className="flex flex-col gap-2.5">
          <h4 className="text-sm font-semibold text-ana">Referanslar</h4>
          {referanslar.map((referans) => (
            <ReferansSatiri
              key={referans.id}
              referans={referans}
              onYenidenIste={() =>
                void calistir(() => referansYenidenIste(referans.id))
              }
              onGeriCek={() =>
                void calistir(() => referansGeriCek(referans.id))
              }
            />
          ))}
        </section>
      ) : null}

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 text-sm text-muted-foreground">Ekle:</span>
          {EKLEME_DUGMELERI.map(({ form, etiket }) => (
            <Button
              key={form}
              type="button"
              size="sm"
              variant="outline"
              aria-expanded={acikForm === form}
              aria-controls={`ekle-${form}-${somutCiktiId}`}
              onClick={() => onAcikForm(acikForm === form ? null : form)}
            >
              <Plus aria-hidden="true" />
              {etiket}
            </Button>
          ))}
        </div>
        {acikForm ? (
          <div
            id={`ekle-${acikForm}-${somutCiktiId}`}
            className="rounded-md border border-kenar bg-zemin px-4 py-4"
          >
            {acikForm === "link" ? (
              <LinkEkleFormu
                kimlik={somutCiktiId}
                bekleniyor={bekleniyor}
                onEkle={(url) => ekle(() => kanitLinkiEkle(somutCiktiId, url))}
                onVazgec={() => onAcikForm(null)}
              />
            ) : acikForm === "dosya" ? (
              <DosyaEkleFormu
                kimlik={somutCiktiId}
                bekleniyor={bekleniyor}
                onEkle={(dosya) =>
                  ekle(() => kanitDosyasiEkle(somutCiktiId, dosya))
                }
                onVazgec={() => onAcikForm(null)}
              />
            ) : (
              <ReferansFormu
                kimlik={somutCiktiId}
                bekleniyor={bekleniyor}
                onIste={(eposta) =>
                  ekle(() => referansIste(somutCiktiId, eposta))
                }
                onVazgec={() => onAcikForm(null)}
              />
            )}
          </div>
        ) : null}
      </section>

      {durum?.dogrulanamadi ? (
        <DogrulanamadiEtiketi notlar={durum.girvak_notlari} />
      ) : null}

      {degerlendirildi || durum?.dogrulanamadi ? (
        <Degerlendirme
          kimlik={somutCiktiId}
          not={durum?.guven_skoru?.gerekce_metni ?? null}
          incelemeBekliyor={durum?.inceleme_bekliyor ?? false}
          kararaItiraz={durum?.dogrulanamadi ?? false}
          bekleniyor={bekleniyor}
          onItiraz={(aciklama) =>
            calistir(() => itirazEt(somutCiktiId, aciklama))
          }
        />
      ) : null}
    </div>
  );
}

function KanitSatiri({
  parca,
  bekleniyor,
  onKaldir,
}: {
  parca: KanitParcasi & { url: string };
  bekleniyor: boolean;
  onKaldir: () => Promise<boolean>;
}) {
  const [onay, setOnay] = useState(false);

  if (onay) {
    return (
      <li>
        <OnayAlani
          soru="Bu kanıt kaldırılsın mı? Çalışman kalan kanıtla yeniden değerlendirilir."
          onayEtiketi="Kaldır"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Kaldırılıyor…"
          onOnayla={() => void onKaldir().then(() => setOnay(false))}
          onVazgec={() => setOnay(false)}
        />
      </li>
    );
  }
  const secenekler = okunamayanSecenekleri(parca);
  return (
    <li className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <a
          href={kanitAdresi(parca.url)}
          target="_blank"
          rel="noreferrer noopener"
          className="min-w-0 text-sm break-all text-baglanti underline underline-offset-4"
        >
          {parca.url}
        </a>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={bekleniyor}
          onClick={() => setOnay(true)}
        >
          Kaldır
        </Button>
      </div>
      {secenekler ? <SecenekKutusu kutu={secenekler} /> : null}
    </li>
  );
}

/** Okunamayan link için açıklama ve gencin yapabilecekleri (docs/dogrulama.md § 3). */
function SecenekKutusu({ kutu }: { kutu: SecenekKutusuVerisi }) {
  return (
    <div className="flex flex-col gap-1 rounded-sm border border-kenar bg-muted/40 px-3 py-2 text-sm">
      <p className="text-pretty">{kutu.mesaj}</p>
      <p className="text-xs text-muted-foreground">
        Bunlardan birini yapabilirsin:
      </p>
      <ul className="flex list-disc flex-col gap-0.5 pl-5 text-xs text-muted-foreground">
        {kutu.hesapBagla ? (
          <li>
            <Link href="/profil#hesaplar" className="text-baglanti underline">
              Hesabını bağla
            </Link>
          </li>
        ) : null}
        {kutu.secenekler.map((secenek) => (
          <li key={secenek}>{secenek}</li>
        ))}
      </ul>
    </div>
  );
}

/** İndirme adresi kısa ömürlü: tıklanınca alınır, dosya indirme olarak açılır. */
async function indir(
  somutCiktiId: string,
  parcaId: string,
  onHata: (hata: Hata | null) => void,
) {
  onHata(null);
  try {
    const { adres } = await kanitDosyasiAdresi(somutCiktiId, parcaId);
    window.location.assign(adres);
  } catch (sebep) {
    onHata(hatayaCevir(sebep));
  }
}

function DosyaSatiri({
  parca,
  bekleniyor,
  onIndir,
  onGorunurluk,
  onKaldir,
}: {
  parca: KanitParcasi;
  bekleniyor: boolean;
  onIndir: () => void;
  onGorunurluk: (gorunur: boolean) => Promise<boolean>;
  onKaldir: () => Promise<boolean>;
}) {
  const [onay, setOnay] = useState(false);
  const kutu = `gorunur-${parca.id}`;
  const inceleme = girvakIncelemesiMetni(parca.girvak_incelemesi);
  const boyut = dosyaBoyutu(parca.dosya_boyutu);

  if (onay) {
    return (
      <li>
        <OnayAlani
          soru="Bu dosya kaldırılsın mı? Dosya silinir ve çalışman kalan kanıtla yeniden değerlendirilir."
          onayEtiketi="Kaldır"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Kaldırılıyor…"
          onOnayla={() => void onKaldir().then(() => setOnay(false))}
          onVazgec={() => setOnay(false)}
        />
      </li>
    );
  }
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={onIndir}
          className="min-w-0 text-left text-sm break-all text-baglanti underline underline-offset-4"
        >
          {parca.dosya_adi ?? (parca.tur === "gorsel" ? "Görsel" : "Dosya")}
        </button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={bekleniyor}
          onClick={() => setOnay(true)}
        >
          Kaldır
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        {parca.tur === "gorsel" ? "Görsel" : "PDF"}
        {boyut ? ` · ${boyut}` : ""}
        {parca.uretim_araci ? ` · Oluşturan araç: ${parca.uretim_araci}` : ""}
      </p>
      {inceleme ? <p className="text-xs text-pretty">{inceleme}</p> : null}
      <label htmlFor={kutu} className="flex w-fit items-center gap-2 text-xs">
        <input
          id={kutu}
          type="checkbox"
          checked={parca.gorunur_firmaya ?? false}
          disabled={bekleniyor}
          onChange={(olay) => void onGorunurluk(olay.target.checked)}
        />
        Firmalar görebilir
      </label>
    </li>
  );
}

function DosyaEkleFormu({
  kimlik,
  bekleniyor,
  onEkle,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onEkle: (dosya: File) => Promise<boolean>;
  onVazgec: () => void;
}) {
  const [dosya, setDosya] = useState<File | null>(null);
  const girdi = useRef<HTMLInputElement>(null);

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (!dosya) return;
        void onEkle(dosya).then((tamam) => {
          if (!tamam) return;
          setDosya(null);
          if (girdi.current) girdi.current.value = "";
        });
      }}
    >
      <FormAlani etiket="PDF ya da görsel ekle" htmlFor={`dosya-${kimlik}`}>
        <Input
          ref={girdi}
          id={`dosya-${kimlik}`}
          type="file"
          accept={KABUL_EDILEN_DOSYALAR}
          onChange={(olay) => setDosya(olay.target.files?.[0] ?? null)}
        />
      </FormAlani>
      <p className="text-xs text-pretty text-muted-foreground">
        Sertifika, rapor, sonuç listesi ya da çalışmanın ekran görüntüsü. PDF en
        çok 20 MB, görsel en çok 10 MB. Dosyayı yalnızca sen ve GİRVAK görür;
        istersen firmalara açabilirsin.
      </p>
      <FormDugmeleri onVazgec={onVazgec}>
        <Button type="submit" size="sm" disabled={bekleniyor || !dosya}>
          {bekleniyor ? "Değerlendiriliyor…" : "Yükle ve değerlendir"}
        </Button>
      </FormDugmeleri>
    </form>
  );
}

function LinkEkleFormu({
  kimlik,
  bekleniyor,
  onEkle,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onEkle: (url: string) => Promise<boolean>;
  onVazgec: () => void;
}) {
  const [link, setLink] = useState("");

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (!link.trim()) return;
        void onEkle(link.trim()).then((tamam) => {
          if (tamam) setLink("");
        });
      }}
    >
      <FormAlani etiket="Kanıt linki ekle" htmlFor={`link-${kimlik}`}>
        <Input
          id={`link-${kimlik}`}
          value={link}
          onChange={(olay) => setLink(olay.target.value)}
          placeholder="ör. github.com/… ya da bir demo adresi"
          inputMode="url"
        />
      </FormAlani>
      <p className="text-xs text-muted-foreground">
        Linkin açılır ve çalışman dört açıdan değerlendirilir.
      </p>
      <FormDugmeleri onVazgec={onVazgec}>
        <Button type="submit" size="sm" disabled={bekleniyor || !link.trim()}>
          {bekleniyor ? "Değerlendiriliyor…" : "Ekle ve değerlendir"}
        </Button>
      </FormDugmeleri>
    </form>
  );
}

function ReferansFormu({
  kimlik,
  bekleniyor,
  onIste,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onIste: (eposta: string) => Promise<boolean>;
  onVazgec: () => void;
}) {
  const [eposta, setEposta] = useState("");

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (!eposta.trim()) return;
        void onIste(eposta.trim()).then((tamam) => {
          if (tamam) setEposta("");
        });
      }}
    >
      <FormAlani etiket="Referans iste" htmlFor={`referans-${kimlik}`}>
        <Input
          id={`referans-${kimlik}`}
          type="email"
          value={eposta}
          onChange={(olay) => setEposta(olay.target.value)}
          placeholder="ör. çalışmanı doğrulayabilecek birinin e-postası"
          autoComplete="off"
        />
      </FormAlani>
      <p className="text-xs text-pretty text-muted-foreground">
        Bu kişiye birkaç kısa soruluk bir e-posta göndeririz; 3. gün bir kez
        hatırlatırız. Yanıt için 7 günü var.
      </p>
      <FormDugmeleri onVazgec={onVazgec}>
        <Button type="submit" size="sm" disabled={bekleniyor || !eposta.trim()}>
          Referans iste
        </Button>
      </FormDugmeleri>
    </form>
  );
}

/** Ekleme formunun gönder ve vazgeç düğmeleri. */
function FormDugmeleri({
  children,
  onVazgec,
}: {
  children: React.ReactNode;
  onVazgec: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {children}
      <Button type="button" size="sm" variant="ghost" onClick={onVazgec}>
        Vazgeç
      </Button>
    </div>
  );
}

/**
 * GİRVAK'ın "doğrulanamadı" kararı (docs/dogrulama.md § 9). Puanı değiştirmez; genç kararı
 * görür ve itiraz edebilir. GİRVAK "sorun yok" derse etiket kalkar.
 */
function DogrulanamadiEtiketi({ notlar }: { notlar: string[] }) {
  return (
    <section
      className="flex flex-col gap-1.5 rounded-sm border border-kenar px-3 py-2"
      aria-label="GİRVAK kararı"
    >
      <span className="w-fit rounded-sm border border-kenar px-2 py-0.5 text-xs font-medium">
        Doğrulanamadı
      </span>
      <p className="text-sm text-pretty">
        GİRVAK bu çalışmayı inceledi ve şimdilik doğrulayamadı. Güven göstergen
        bu yüzden değişmedi; karara aşağıdan itiraz edebilirsin.
      </p>
      {notlar.map((not, i) => (
        <p key={i} className="text-sm text-pretty">
          <span className="text-muted-foreground">GİRVAK’ın notu: </span>
          {not}
        </p>
      ))}
    </section>
  );
}

function Degerlendirme({
  kimlik,
  not,
  incelemeBekliyor,
  kararaItiraz,
  bekleniyor,
  onItiraz,
}: {
  kimlik: string;
  not: string | null;
  incelemeBekliyor: boolean;
  kararaItiraz: boolean;
  bekleniyor: boolean;
  onItiraz: (aciklama: string) => Promise<boolean>;
}) {
  const [acik, setAcik] = useState(false);
  const [aciklama, setAciklama] = useState("");
  const notlar = notuBasliklaraAyir(not);

  return (
    <section className="flex flex-col gap-3 border-t border-kenar pt-4">
      {notlar.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold text-ana">
            Değerlendirme notları
          </h4>
          <ul className="flex flex-col gap-2">
            {notlar.map((parca, i) => (
              <li
                key={i}
                className="grid gap-x-3 gap-y-0.5 text-sm text-pretty sm:grid-cols-[5rem_1fr]"
              >
                <span className="font-medium text-metin">
                  {parca.baslik ?? "Genel"}
                </span>
                <span className="text-muted-foreground">{parca.metin}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {incelemeBekliyor ? (
        // İtiraz hakkı doldu; son itiraz GİRVAK'ta (docs/dogrulama.md § 9). Karar bildirimle gelir.
        <p className="text-sm text-muted-foreground text-pretty" role="status">
          İtirazın GİRVAK’a iletildi; inceleyip sonucu sana bildirecek. Yeni bir
          kanıt eklersen çalışman yeniden değerlendirilir.
        </p>
      ) : acik ? (
        <form
          className="flex flex-col gap-3"
          onSubmit={(olay) => {
            olay.preventDefault();
            if (aciklama.trim().length < 3) return;
            void onItiraz(aciklama.trim()).then((tamam) => {
              if (tamam) {
                setAciklama("");
                setAcik(false);
              }
            });
          }}
        >
          <FormAlani etiket="İtiraz nedeni" htmlFor={`itiraz-${kimlik}`}>
            <Input
              id={`itiraz-${kimlik}`}
              value={aciklama}
              onChange={(olay) => setAciklama(olay.target.value)}
              placeholder="ör. rolüm açıklamada net yazmıyordu"
            />
          </FormAlani>
          <p className="text-xs text-muted-foreground">
            {kararaItiraz
              ? "Neyin gözden kaçtığını yaz; itirazın GİRVAK’a gider ve sonucu sana bildirilir."
              : "Neyin gözden kaçtığını yaz; yeni bir kanıtın varsa yukarıdan ekle. Güven göstergesi yeniden hesaplanır, referans yanıtı korunur."}
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              type="submit"
              size="sm"
              disabled={bekleniyor || aciklama.trim().length < 3}
            >
              {bekleniyor ? "Yeniden bakılıyor…" : "İtirazı gönder"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAcik(false)}
            >
              Vazgeç
            </Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setAcik(true)}
          >
            {kararaItiraz ? "Karara itiraz et" : "Değerlendirmeye itiraz et"}
          </Button>
          <span className="text-xs text-muted-foreground">
            {kararaItiraz
              ? "GİRVAK’ın yeniden bakmasını isteyebilirsin."
              : "Değerlendirmeyi eksik buluyorsan yeniden bakılmasını isteyebilirsin."}
          </span>
        </div>
      )}
    </section>
  );
}

function ReferansSatiri({
  referans,
  onYenidenIste,
  onGeriCek,
}: {
  referans: ReferansDurumu;
  onYenidenIste: () => void;
  onGeriCek: () => void;
}) {
  // İş değiştiyse eski yanıt geçmişte kalır (docs/kararlar.md G8).
  const { not, yenidenIstenebilir } = referansSatiri(referans);
  const { yanitlar, isaretler } = referansOzeti(referans);
  const [onayAcik, setOnayAcik] = useState(false);

  return (
    <div className="flex flex-col gap-1 rounded-sm border border-kenar px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm break-all">{referans.referans_email}</span>
        <span className="text-xs text-muted-foreground">
          {REFERANS_DURUMLARI[referans.durum] ?? referans.durum}
        </span>
      </div>

      {yanitlar.length > 0 ? (
        <p className="text-sm">{yanitlar.join(" · ")}</p>
      ) : null}
      {isaretler.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5" aria-label="Referans hakkında">
          {isaretler.map((isaret) => (
            <li
              key={isaret}
              className="rounded-sm border border-kenar px-2 py-0.5 text-xs text-muted-foreground"
            >
              {isaret}
            </li>
          ))}
        </ul>
      ) : null}

      {referans.yanit_metni ? (
        <p className="text-sm text-pretty text-muted-foreground">
          “{referans.yanit_metni}”
        </p>
      ) : null}

      {referans.geri_cekilebilir && onayAcik ? (
        <OnayAlani
          soru={`${referans.referans_email} adresine giden istek geri çekilsin mi? Bağlantı artık açılmaz; doğru adresle yeni bir referans isteyebilirsin.`}
          onayEtiketi="İsteği geri çek"
          onOnayla={() => {
            setOnayAcik(false);
            onGeriCek();
          }}
          onVazgec={() => setOnayAcik(false)}
        />
      ) : referans.geri_cekilebilir ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="w-fit"
          onClick={() => setOnayAcik(true)}
        >
          Geri çek
        </Button>
      ) : null}

      {not ? (
        <p className="text-xs text-pretty text-muted-foreground">{not}</p>
      ) : null}
      {yenidenIstenebilir ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-fit"
          onClick={onYenidenIste}
        >
          Referansı yeniden iste
        </Button>
      ) : null}
    </div>
  );
}
