"use client";

import { useState } from "react";

import { OnayAlani } from "@/components/onay-alani";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type KanitDurumu,
  type KanitParcasi,
  type ReferansDurumu,
  itirazEt,
  kalemiDegerlendir,
  kanitLinkiEkle,
  kanitParcasiSil,
  referansGeriCek,
  referansIste,
  referansYenidenIste,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { degerlendirildiMi, kanitAdresi, kanitLinkleri } from "@/lib/kanit";
import { referansSatiri } from "@/lib/kart-duzenleme";
import { REFERANS_DURUMLARI, referansOzeti } from "@/lib/referans";

/**
 * Bir çalışmanın kanıt bölümü (docs/plans/dogrulama-iyilestirme.md § 3).
 *
 * Dört iş, dört ayrı eylem:
 *   - Kanıtlar: link eklenir (çalışma hemen değerlendirilir) ya da kaldırılır.
 *     Kanıt yalnızca buradan değişir; iddia düzenleme formu linke dokunmaz.
 *   - Değerlendirme: linki olup henüz değerlendirilmemiş çalışma için.
 *   - Referans: istemek değerlendirmeyi yeniden çalıştırmaz. E-postayı sistem
 *     gönderir; yanıt linki gence gösterilmez (plan § 7, adım 7). Yanlış
 *     adrese giden bekleyen istek geri çekilebilir.
 *   - İtiraz: değerlendirmeyi eksik bulan genç yeniden baktırır.
 */

export function KanitBolumu({
  somutCiktiId,
  kanitlar,
  durum,
  onDurum,
  onHata,
}: {
  somutCiktiId: string;
  /** Kart görünümündeki kanıtlar: kanıt durumu gelmeden de liste çizilsin. */
  kanitlar: KanitParcasi[];
  durum: KanitDurumu | undefined;
  onDurum: (durum: KanitDurumu) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const linkler = kanitLinkleri(durum?.kanitlar ?? kanitlar);
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

  return (
    <div className="flex flex-col gap-5 rounded-sm border border-kenar bg-card px-4 py-4">
      <section className="flex flex-col gap-3">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Kanıtlar
        </h4>
        {linkler.length > 0 ? (
          <ul className="flex flex-col gap-2">
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
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Henüz kanıt eklemedin. Bir link ya da aşağıdan bir referans
            ekleyebilirsin.
          </p>
        )}
        <LinkEkleFormu
          kimlik={somutCiktiId}
          bekleniyor={bekleniyor}
          onEkle={(url) => calistir(() => kanitLinkiEkle(somutCiktiId, url))}
        />
        {linkler.length > 0 && durum && !degerlendirildi ? (
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

      <section className="flex flex-col gap-3 border-t border-kenar pt-4">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Referanslar
        </h4>
        {durum && durum.referanslar.length > 0
          ? durum.referanslar.map((referans) => (
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
            ))
          : null}
        <ReferansFormu
          kimlik={somutCiktiId}
          bekleniyor={bekleniyor}
          onIste={(eposta) =>
            calistir(() => referansIste(somutCiktiId, eposta))
          }
        />
      </section>

      {degerlendirildi ? (
        <Degerlendirme
          kimlik={somutCiktiId}
          not={durum?.guven_skoru?.gerekce_metni ?? null}
          incelemeBekliyor={durum?.inceleme_bekliyor ?? false}
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
  return (
    <li className="flex flex-wrap items-center justify-between gap-2">
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
    </li>
  );
}

function LinkEkleFormu({
  kimlik,
  bekleniyor,
  onEkle,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onEkle: (url: string) => Promise<boolean>;
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
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={bekleniyor || !link.trim()}>
          {bekleniyor ? "Değerlendiriliyor…" : "Ekle ve değerlendir"}
        </Button>
        <span className="text-xs text-muted-foreground">
          Linkin açılır ve çalışman dört açıdan değerlendirilir.
        </span>
      </div>
    </form>
  );
}

function ReferansFormu({
  kimlik,
  bekleniyor,
  onIste,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onIste: (eposta: string) => Promise<boolean>;
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
      <Button
        type="submit"
        size="sm"
        variant="outline"
        className="w-fit"
        disabled={bekleniyor || !eposta.trim()}
      >
        Referans iste
      </Button>
    </form>
  );
}

function Degerlendirme({
  kimlik,
  not,
  incelemeBekliyor,
  bekleniyor,
  onItiraz,
}: {
  kimlik: string;
  not: string | null;
  incelemeBekliyor: boolean;
  bekleniyor: boolean;
  onItiraz: (aciklama: string) => Promise<boolean>;
}) {
  const [acik, setAcik] = useState(false);
  const [aciklama, setAciklama] = useState("");

  return (
    <section className="flex flex-col gap-3 border-t border-kenar pt-4">
      {not ? (
        <p className="text-sm text-pretty">
          <span className="text-muted-foreground">Değerlendirme notu: </span>
          {not}
        </p>
      ) : null}

      {incelemeBekliyor ? (
        // İtiraz hakkı doldu; son itiraz GİRVAK'ta (plan § 9). Karar bildirimle gelir.
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
            Neyin gözden kaçtığını yaz; yeni bir kanıtın varsa yukarıdan ekle.
            Güven göstergesi yeniden hesaplanır, referans yanıtı korunur.
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
            Değerlendirmeye itiraz et
          </Button>
          <span className="text-xs text-muted-foreground">
            Değerlendirmeyi eksik buluyorsan yeniden bakılmasını isteyebilirsin.
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
  // İş değiştiyse eski yanıt geçmişte kalır (docs/plans/genc-akisi.md § 0, karar 8).
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
