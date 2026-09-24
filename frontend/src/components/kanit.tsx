"use client";

import { useState } from "react";

import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type KanitDurumu,
  type ReferansDurumu,
  itirazEt,
  kanitEkle,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * Bir somut çıktının kanıt/referans bölümü (docs/agent-specs.md § 4).
 *
 * Üç akış da burada: kanıt ekleme (ön rubrik), referans isteği ve itiraz.
 * Referans yanıt linki ekranda gösteriliyor çünkü SMTP kurmuyoruz — bilinen
 * MVP sınırlaması, README'de de yazıyor.
 */

const REFERANS_DURUMLARI: Record<string, string> = {
  bekliyor: "Yanıt bekleniyor",
  yanitlandi: "Yanıtladı",
  yanit_yok: "Süresinde yanıt gelmedi",
};

export function KanitBolumu({
  somutCiktiId,
  durum,
  onDurum,
  onHata,
}: {
  somutCiktiId: string;
  durum: KanitDurumu | undefined;
  onDurum: (durum: KanitDurumu) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const [link, setLink] = useState("");
  const [tur, setTur] = useState("");
  const [referansEmail, setReferansEmail] = useState("");
  const [aciklama, setAciklama] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [itirazAcik, setItirazAcik] = useState(false);

  const puanlanmis = Boolean(durum?.guven_skoru);

  async function calistir(is: () => Promise<KanitDurumu>) {
    onHata(null);
    setBekleniyor(true);
    try {
      onDurum(await is());
      setLink("");
      setTur("");
      setReferansEmail("");
      setAciklama("");
      setItirazAcik(false);
    } catch (sebep) {
      onHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-sm border border-kenar bg-card px-4 py-4">
      {durum && durum.referanslar.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h4 className="font-heading text-sm font-semibold text-ana">
            Referans istekleri
          </h4>
          {durum.referanslar.map((referans) => (
            <ReferansSatiri key={referans.id} referans={referans} />
          ))}
        </section>
      ) : null}

      <form
        className="flex flex-col gap-3"
        onSubmit={(olay) => {
          olay.preventDefault();
          if (!link.trim() && !referansEmail.trim()) return;
          void calistir(() =>
            kanitEkle({
              somut_cikti_id: somutCiktiId,
              kanit_linki: link.trim() || null,
              kanit_turu: tur.trim() || null,
              referans_email: referansEmail.trim() || null,
            }),
          );
        }}
      >
        <h4 className="font-heading text-sm font-semibold text-ana">
          {puanlanmis ? "Kanıtı güncelle" : "Kanıt ekle"}
        </h4>

        <FormAlani etiket="Kanıt linki" htmlFor={`link-${somutCiktiId}`}>
          <Input
            id={`link-${somutCiktiId}`}
            value={link}
            onChange={(olay) => setLink(olay.target.value)}
            placeholder="github.com/… veya bir demo adresi"
            inputMode="url"
          />
        </FormAlani>

        <div className="grid gap-3 sm:grid-cols-2">
          <FormAlani
            etiket="Kanıt türü"
            htmlFor={`tur-${somutCiktiId}`}
            istegeBagli
          >
            <Input
              id={`tur-${somutCiktiId}`}
              value={tur}
              onChange={(olay) => setTur(olay.target.value)}
              placeholder="kod deposu, rapor, video…"
            />
          </FormAlani>

          <FormAlani
            etiket="Referans e-postası"
            htmlFor={`referans-${somutCiktiId}`}
            istegeBagli
          >
            <Input
              id={`referans-${somutCiktiId}`}
              type="email"
              value={referansEmail}
              onChange={(olay) => setReferansEmail(olay.target.value)}
              placeholder="isi-dogrulayabilecek@ornek.com"
              autoComplete="off"
            />
          </FormAlani>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="submit"
            size="lg"
            disabled={bekleniyor || (!link.trim() && !referansEmail.trim())}
          >
            {bekleniyor ? "Değerlendiriliyor…" : "Kaydet ve değerlendir"}
          </Button>
          <span className="text-xs text-muted-foreground">
            Kanıt linki açılıp okunur, sonra dört başlıkta puanlanır.
          </span>
        </div>
      </form>

      {puanlanmis ? (
        <section className="flex flex-col gap-3 border-t border-kenar pt-4">
          {durum?.guven_skoru?.gerekce_metni ? (
            <p className="text-sm text-pretty">
              <span className="text-muted-foreground">Ajanın notu: </span>
              {durum.guven_skoru.gerekce_metni}
            </p>
          ) : null}

          {itirazAcik ? (
            <form
              className="flex flex-col gap-3"
              onSubmit={(olay) => {
                olay.preventDefault();
                void calistir(() =>
                  itirazEt(
                    somutCiktiId,
                    link.trim() || null,
                    aciklama.trim() || null,
                  ),
                );
              }}
            >
              <FormAlani
                etiket="Neden itiraz ediyorsun?"
                htmlFor={`itiraz-${somutCiktiId}`}
                istegeBagli
              >
                <Input
                  id={`itiraz-${somutCiktiId}`}
                  value={aciklama}
                  onChange={(olay) => setAciklama(olay.target.value)}
                  placeholder="Örn. rolüm açıklamada net yazmıyordu"
                />
              </FormAlani>
              <p className="text-xs text-muted-foreground">
                Yukarıdaki kanıt linkini doldurduysan yeni link kullanılır. Puan
                yeniden hesaplanır; referans yanıtı korunur.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button type="submit" size="lg" disabled={bekleniyor}>
                  {bekleniyor ? "Yeniden bakılıyor…" : "İtirazı gönder"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={() => setItirazAcik(false)}
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
                size="lg"
                onClick={() => setItirazAcik(true)}
              >
                Puana itiraz et
              </Button>
              <span className="text-xs text-muted-foreground">
                Puanı düşük buluyorsan yeniden değerlendirilmesini
                isteyebilirsin.
              </span>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

/**
 * Referans kişiye iletilecek link — tam adres.
 *
 * Göreli bir yol ("/referans?token=…") kopyalanıp e-postayla gönderilince
 * çalışmıyor; referans kişi bu sayfayı bizim sitemizde açacak. Bu yüzden
 * adres origin'le birlikte gösteriliyor ve kopyalanabiliyor.
 */
function YanitLinki({ adres }: { adres: string }) {
  const [kopyalandi, setKopyalandi] = useState(false);

  async function kopyala() {
    try {
      await navigator.clipboard.writeText(adres);
      setKopyalandi(true);
      window.setTimeout(() => setKopyalandi(false), 2000);
    } catch {
      // Pano izni yoksa link zaten ekranda; elle seçilip kopyalanabilir.
      setKopyalandi(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs text-muted-foreground">
        Yanıt linki — e-posta göndermiyoruz, referans kişiye kendin ilet:
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <a
          className="text-xs break-all text-baglanti underline underline-offset-4"
          href={adres}
        >
          {adres}
        </a>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void kopyala()}
        >
          {kopyalandi ? "Kopyalandı" : "Kopyala"}
        </Button>
      </div>
    </div>
  );
}

/**
 * Backend girişsiz yanıt uç noktasının yolunu döndürüyor; referans kişiye
 * gösterilecek olan ise onu saran sayfanın TAM adresi.
 */
function yanitSayfasiLinki(yanitLinki: string | null): string | null {
  if (!yanitLinki) return null;
  const token = new URLSearchParams(yanitLinki.split("?")[1] ?? "").get(
    "token",
  );
  if (!token) return null;
  // Bileşen yalnızca veri geldikten sonra çiziliyor, yani tarayıcıdayız.
  const koken = typeof window === "undefined" ? "" : window.location.origin;
  return `${koken}/referans?token=${encodeURIComponent(token)}`;
}

function ReferansSatiri({ referans }: { referans: ReferansDurumu }) {
  const yanitSayfasi = yanitSayfasiLinki(referans.yanit_linki);

  return (
    <div className="flex flex-col gap-1 rounded-sm border border-kenar px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm break-all">{referans.referans_email}</span>
        <span className="text-xs text-muted-foreground">
          {REFERANS_DURUMLARI[referans.durum] ?? referans.durum}
          {referans.puan !== null ? ` · ${referans.puan}/5` : ""}
        </span>
      </div>

      {referans.yanit_metni ? (
        <p className="text-sm text-pretty text-muted-foreground">
          “{referans.yanit_metni}”
        </p>
      ) : null}

      {referans.durum === "bekliyor" && yanitSayfasi ? (
        <YanitLinki adres={yanitSayfasi} />
      ) : null}
    </div>
  );
}
