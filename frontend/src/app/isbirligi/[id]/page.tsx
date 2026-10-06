"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  DurumEtiketi,
  IletisimSatiri,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { OnayAlani } from "@/components/onay-alani";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type IsbirligiDetayi,
  type MilestoneGirdisi,
  type MilestoneYaniti,
  type SonlanmaNedeni,
  isbirligiGetir,
  isbirligiSonlandir,
  milestoneEkle,
  milestoneGuncelle,
  milestoneIsaretiGeriAl,
  milestoneIsaretle,
  milestoneSil,
  planOner,
  planOnayla,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { type Hitap, hitapla } from "@/lib/hitap";
import { useHitap, useOturum } from "@/lib/oturum";
import {
  ISBIRLIGI_DURUM_ETIKETLERI,
  SONLANMA_NEDENLERI,
  type Taraf,
  adimGorunumu,
  planOnayGorunumu,
  tarafim,
} from "@/lib/takip";
import { panelYolu } from "@/lib/yonlendirme";

/**
 * İş birliği sayfası, Takip Ajanı (docs/faz-c-takip.md § 8). Kullanıcıya
 * "ajan" denmez; hitap bakan hesaba göre (rehber § 3).
 *
 * İki tarafa aynı sayfa. Üç hâl:
 *   plan_bekliyor — ajanın önerdiği plan düzenlenir, iki taraf onaylar;
 *   aktif         — adımlar iki taraflı işaretlenir, gecikme görünür;
 *   tamamlandi    — son adımla kendiliğinden; gencin kartında tamamlanan iş birliği.
 * GİRVAK yalnızca okur. Ajan karar vermez: plan ve özet önerir, hiçbir adımı
 * kendisi kapatmaz.
 */

// Kabulden hemen sonra plan arka planda hazırlanıyor; sayfa bir süre bekler.
const PLAN_BEKLEME_ARALIGI_MS = 4000;
const PLAN_BEKLEME_EN_COK = 8;

export default function IsbirligiSayfasi() {
  return (
    <GirisKapisi>
      <IsbirligiIcerigi />
    </GirisKapisi>
  );
}

function IsbirligiIcerigi() {
  const { id } = useParams<{ id: string }>();
  const hesap = useGirisliHesap();
  const { tazele } = useOturum();
  const hitap = useHitap();
  // Taraf rolden değil eşleşmeden: ortak firmanın rolü de "kurum"
  // (docs/plans/firma-akisi.md § 9). Detay gelene kadar rolden tahmin.
  const rolTarafi = tarafim(hesap.rol);

  const [detay, setDetay] = useState<IsbirligiDetayi | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const [bekleniyor, setBekleniyor] = useState(false);
  const okundu = useRef(false);
  const [beklemeSayisi, setBeklemeSayisi] = useState(0);

  const oku = useCallback(async () => {
    try {
      setDetay(await isbirligiGetir(id));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [id]);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  // Plan henüz gelmediyse (arka plan işi sürüyor olabilir) kısa aralıkla yokla.
  const planBekleniyor =
    detay !== null &&
    detay.durum === "plan_bekliyor" &&
    detay.milestonelar.length === 0 &&
    !detay.plan_onerildi_mi;
  useEffect(() => {
    if (!planBekleniyor || beklemeSayisi >= PLAN_BEKLEME_EN_COK) return;
    const zamanlayici = window.setTimeout(() => {
      setBeklemeSayisi((sayi) => sayi + 1);
      void oku();
    }, PLAN_BEKLEME_ARALIGI_MS);
    return () => window.clearTimeout(zamanlayici);
  }, [planBekleniyor, beklemeSayisi, oku]);

  /** Her eylem güncel görünümü döner; hata olursa görünüm olduğu gibi kalır. */
  async function yap(eylem: () => Promise<IsbirligiDetayi>) {
    setHata(null);
    setBekleniyor(true);
    try {
      setDetay(await eylem());
      void tazele(); // bildirim rozeti
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  if (!detay) {
    return <SayfaDurumu hata={hata} tekrarDene={() => void oku()} />;
  }

  const taraf: Taraf | null =
    detay.tarafim !== undefined ? detay.tarafim : rolTarafi;
  const karsiTaraf: Taraf | null =
    taraf === "genc" ? "kurum" : taraf === "kurum" ? "genc" : null;

  return (
    <Sayfa>
      <SayfaBasligi
        baslik={`${detay.kurum_adi} · ${detay.aday_adi}`}
        etiket={
          <DurumEtiketi
            metin={ISBIRLIGI_DURUM_ETIKETLERI[detay.durum] ?? detay.durum}
            baglanti={detay.durum === "tamamlandi"}
          />
        }
        aciklama={
          <>
            {detay.rol_alani ?? "İş birliği ortağı"} ·{" "}
            {tarihYaz(detay.baslangic_tarihi)} tarihinde başladı
          </>
        }
      >
        <p className="border-l-2 border-kenar pl-3 text-sm text-pretty">
          {detay.problem_tanimi}
          {detay.basari_kriteri ? (
            <span className="mt-1 block text-muted-foreground">
              Başarı ölçütü: {detay.basari_kriteri}
            </span>
          ) : null}
        </p>
        {detay.iletisim && karsiTaraf ? (
          <IletisimSatiri iletisim={detay.iletisim} karsiTaraf={karsiTaraf} />
        ) : null}
      </SayfaBasligi>

      {detay.durum === "tamamlandi" ? (
        <TamamlandiBandi detay={detay} taraf={taraf} hitap={hitap} />
      ) : null}
      {detay.durum === "sonlandi" ? <SonlandiBandi hitap={hitap} /> : null}

      {detay.durum_ozeti ? (
        <section className="flex flex-col gap-1 rounded-sm border border-kenar bg-card px-4 py-3">
          <span className="text-xs text-muted-foreground">
            Durum özeti · {tarihYaz(detay.ozet_tarihi, true)}
          </span>
          <p className="text-sm text-pretty">{detay.durum_ozeti}</p>
        </section>
      ) : null}

      {hata ? <HataKutusu hata={hata} /> : null}

      {detay.durum === "plan_bekliyor" ? (
        <PlanTaslagi
          detay={detay}
          taraf={taraf}
          hitap={hitap}
          bekleniyor={bekleniyor}
          planBekleniyor={planBekleniyor && beklemeSayisi < PLAN_BEKLEME_EN_COK}
          yap={yap}
        />
      ) : (
        <ZamanCizelgesi
          detay={detay}
          taraf={taraf}
          hitap={hitap}
          bekleniyor={bekleniyor}
          yap={yap}
        />
      )}

      {taraf && (detay.durum === "plan_bekliyor" || detay.durum === "aktif") ? (
        <SureciSonlandir detay={detay} bekleniyor={bekleniyor} yap={yap} />
      ) : null}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href={panelYolu(hesap.rol)}>Panele dön</Link>
        </Button>
      </footer>
    </Sayfa>
  );
}

type Yap = (eylem: () => Promise<IsbirligiDetayi>) => Promise<void>;

/* --- Tamamlandı ----------------------------------------------------------- */

function TamamlandiBandi({
  detay,
  taraf,
  hitap,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  hitap: Hitap;
}) {
  return (
    <section className="flex flex-col gap-2 rounded-sm border border-baglanti bg-card px-4 py-4">
      <p className="font-heading text-lg font-semibold text-ana">
        İş birliği tamamlandı
      </p>
      <p className="text-sm text-pretty">
        {detay.ilerleme.toplam} adımın hepsi iki tarafça onaylandı ·{" "}
        {tarihYaz(detay.tamamlanma_tarihi)}
      </p>
      {taraf === "genc" ? (
        <p className="text-sm text-pretty">
          {hitapla(
            hitap,
            "Kartında tamamlanan iş birliği olarak görünür; yeni fırsatlarda seni öne çıkarır.",
            "Kartınızda tamamlanan iş birliği olarak görünür; yeni fırsatlarda sizi öne çıkarır.",
          )}
          {detay.yetenek_karti_id ? (
            <>
              {" "}
              <Link
                href={`/kart/${detay.yetenek_karti_id}`}
                className="text-baglanti underline"
              >
                Kartını gör
              </Link>
            </>
          ) : null}
        </p>
      ) : null}
    </section>
  );
}

/* --- Erken sonlanma ------------------------------------------------------- */

function SonlandiBandi({ hitap }: { hitap: Hitap }) {
  return (
    <section className="flex flex-col gap-1 rounded-sm border border-kenar bg-card px-4 py-4">
      <p className="font-heading text-lg font-semibold text-ana">
        Bu süreç sonlandı
      </p>
      <p className="text-sm text-pretty text-muted-foreground">
        {hitapla(
          hitap,
          "Adımlar kayıtlı kalır ama artık değiştirilemez. Yeni fırsatlar panelinde görünmeye devam eder.",
          "Adımlar kayıtlı kalır ama artık değiştirilemez. Yeni eşleşmeler panelinizde görünmeye devam eder.",
        )}
      </p>
    </section>
  );
}

/** "Süreci sonlandır": nedeni seçilir, sayfa içinde onaylanır (OnayAlani). */
function SureciSonlandir({
  detay,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const [acik, setAcik] = useState(false);
  const [neden, setNeden] = useState<SonlanmaNedeni>("karar_olumsuz");

  if (!acik) {
    return (
      <div>
        <button
          type="button"
          disabled={bekleniyor}
          onClick={() => setAcik(true)}
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
        >
          Süreci sonlandır
        </button>
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-sm border border-kenar px-4 py-4">
      <FormAlani etiket="Neden" htmlFor="sonlanma-nedeni">
        <select
          id="sonlanma-nedeni"
          value={neden}
          onChange={(olay) => setNeden(olay.target.value as SonlanmaNedeni)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
        >
          {SONLANMA_NEDENLERI.map((secenek) => (
            <option key={secenek.deger} value={secenek.deger}>
              {secenek.etiket}
            </option>
          ))}
        </select>
      </FormAlani>
      <OnayAlani
        soru="Süreç sonlandırılacak ve bu geri alınamaz. Karşı tarafa yalnızca sürecin sonlandığı bildirilir; nedeni gösterilmez."
        onayEtiketi="Süreci sonlandır"
        bekleniyor={bekleniyor}
        bekleniyorEtiketi="Sonlandırılıyor…"
        onOnayla={() =>
          void yap(() => isbirligiSonlandir(detay.id, neden)).then(() =>
            setAcik(false),
          )
        }
        onVazgec={() => setAcik(false)}
      />
    </section>
  );
}

/* --- Süreç çizgisi (plan taslağı ve zaman çizelgesi ortak) ----------------- */

const SUREC_CIZGISI = "relative flex flex-col gap-5 border-l border-kenar pl-5";

function CizgiNoktasi({ tamamlandi }: { tamamlandi: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={
        tamamlandi
          ? "absolute top-1.5 -left-[25px] size-2.5 rounded-full bg-baglanti"
          : "absolute top-1.5 -left-[25px] size-2.5 rounded-full border border-kenar bg-zemin"
      }
    />
  );
}

/** Adımın "ne olunca tamam" cümlesi ve açılır hazırlık önerisi. */
function AdimMetinleri({ adim }: { adim: MilestoneYaniti }) {
  return (
    <>
      {adim.aciklama ? (
        <p className="text-sm text-pretty text-muted-foreground">
          {adim.aciklama}
        </p>
      ) : null}
      {adim.oneri ? (
        <details className="group text-sm">
          <summary className="w-fit cursor-pointer text-baglanti underline-offset-4 hover:underline">
            Hazırlık önerisi
          </summary>
          <p className="mt-1 border-l-2 border-kenar pl-3 text-pretty">
            {adim.oneri}
          </p>
        </details>
      ) : null}
    </>
  );
}

/* --- Plan taslağı --------------------------------------------------------- */

function PlanTaslagi({
  detay,
  taraf,
  hitap,
  bekleniyor,
  planBekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  hitap: Hitap;
  bekleniyor: boolean;
  planBekleniyor: boolean;
  yap: Yap;
}) {
  const onay = planOnayGorunumu(detay, taraf, hitap);
  const adimlar = detay.milestonelar;
  const [yenidenOnay, setYenidenOnay] = useState(false);

  return (
    <PanelBolumu
      id="plan"
      baslik={detay.surec_adi ?? "Plan"}
      aciklama="Adımlar bu tür iş birliklerinde izlenen yoldan gelir ve bu ihtiyaca göre uyarlanır; her adımda bir hazırlık önerisi var. İki taraf düzenleyip onaylar; onaylanan plan değiştirilemez."
    >
      <p className="text-sm text-pretty">{onay.metin}</p>

      {adimlar.length === 0 ? (
        <div className="flex flex-col items-start gap-3 rounded-sm border border-dashed border-kenar px-5 py-4">
          <p className="text-sm text-pretty text-muted-foreground">
            {planBekleniyor
              ? "Plan önerisi hazırlanıyor…"
              : hitapla(
                  hitap,
                  "Henüz plan yok. Plan önerisi alabilir ya da adımları kendin ekleyebilirsin.",
                  "Henüz plan yok. Plan önerisi alabilir ya da adımları kendiniz ekleyebilirsiniz.",
                )}
          </p>
          {taraf ? (
            <Button
              type="button"
              size="lg"
              disabled={bekleniyor}
              onClick={() => void yap(() => planOner(detay.id))}
            >
              {bekleniyor ? "Plan hazırlanıyor…" : "Plan önerisi al"}
            </Button>
          ) : null}
        </div>
      ) : (
        <ol className={SUREC_CIZGISI}>
          {adimlar.map((adim) => (
            <TaslakAdim
              key={adim.id}
              detay={detay}
              adim={adim}
              duzenlenebilir={taraf !== null}
              bekleniyor={bekleniyor}
              yap={yap}
            />
          ))}
        </ol>
      )}

      {taraf ? (
        <>
          <AdimEkle detay={detay} bekleniyor={bekleniyor} yap={yap} />
          <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-4">
            <Button
              type="button"
              size="lg"
              disabled={bekleniyor || adimlar.length === 0 || onay.benOnayladim}
              onClick={() => void yap(() => planOnayla(detay.id))}
            >
              {onay.benOnayladim
                ? hitapla(hitap, "Planı onayladın", "Planı onayladınız")
                : "Planı onayla"}
            </Button>
            {adimlar.length > 0 && !yenidenOnay ? (
              <Button
                type="button"
                size="lg"
                variant="outline"
                disabled={bekleniyor}
                onClick={() => setYenidenOnay(true)}
              >
                Yeni plan önerisi al
              </Button>
            ) : null}
          </div>
          {yenidenOnay ? (
            <OnayAlani
              soru="Yeni bir plan önerisi hazırlanacak; mevcut adımlar silinir ve iki onay da sıfırlanır."
              onayEtiketi="Yeni plan önerisi al"
              bekleniyor={bekleniyor}
              bekleniyorEtiketi="Plan hazırlanıyor…"
              onOnayla={() =>
                void yap(() => planOner(detay.id)).then(() =>
                  setYenidenOnay(false),
                )
              }
              onVazgec={() => setYenidenOnay(false)}
            />
          ) : null}
        </>
      ) : null}
    </PanelBolumu>
  );
}

function TaslakAdim({
  detay,
  adim,
  duzenlenebilir,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  adim: MilestoneYaniti;
  duzenlenebilir: boolean;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const [duzenleniyor, setDuzenleniyor] = useState(false);

  if (duzenleniyor) {
    return (
      <li className="relative">
        <CizgiNoktasi tamamlandi={false} />
        <AdimFormu
          baslangic={adim}
          dugme="Kaydet"
          bekleniyor={bekleniyor}
          onVazgec={() => setDuzenleniyor(false)}
          onGonder={async (girdi) => {
            await yap(() => milestoneGuncelle(detay.id, adim.id, girdi));
            setDuzenleniyor(false);
          }}
        />
      </li>
    );
  }

  return (
    <li className="relative flex flex-col gap-1.5">
      <CizgiNoktasi tamamlandi={false} />
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-medium text-ana">{adim.baslik}</span>
        <span className="text-xs text-muted-foreground">
          {adim.hedef_tarih
            ? `hedef ${tarihYaz(adim.hedef_tarih)}`
            : "tarihsiz"}
        </span>
      </div>
      <AdimMetinleri adim={adim} />
      {duzenlenebilir ? (
        <div className="flex gap-3 pt-1">
          <button
            type="button"
            disabled={bekleniyor}
            onClick={() => setDuzenleniyor(true)}
            className="text-sm text-baglanti underline-offset-4 hover:underline"
          >
            Düzenle
          </button>
          <button
            type="button"
            disabled={bekleniyor}
            onClick={() => void yap(() => milestoneSil(detay.id, adim.id))}
            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
          >
            Sil
          </button>
        </div>
      ) : null}
    </li>
  );
}

function AdimEkle({
  detay,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const [acik, setAcik] = useState(false);
  if (!acik) {
    return (
      <button
        type="button"
        onClick={() => setAcik(true)}
        className="w-fit text-sm text-baglanti underline-offset-4 hover:underline"
      >
        Adım ekle
      </button>
    );
  }
  return (
    <div className="rounded-sm border border-dashed border-kenar px-4 py-3">
      <AdimFormu
        dugme="Adımı ekle"
        bekleniyor={bekleniyor}
        onVazgec={() => setAcik(false)}
        onGonder={async (girdi) => {
          await yap(() =>
            milestoneEkle(detay.id, { ...girdi, baslik: girdi.baslik ?? "" }),
          );
          setAcik(false);
        }}
      />
    </div>
  );
}

function AdimFormu({
  baslangic,
  dugme,
  bekleniyor,
  onVazgec,
  onGonder,
}: {
  baslangic?: MilestoneYaniti;
  dugme: string;
  bekleniyor: boolean;
  onVazgec: () => void;
  onGonder: (girdi: MilestoneGirdisi) => Promise<void>;
}) {
  const [baslik, setBaslik] = useState(baslangic?.baslik ?? "");
  const [aciklama, setAciklama] = useState(baslangic?.aciklama ?? "");
  const [hedef, setHedef] = useState(baslangic?.hedef_tarih ?? "");
  const kimlik = baslangic?.id ?? "yeni";

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(olay) => {
        olay.preventDefault();
        void onGonder({
          baslik: baslik.trim(),
          aciklama: aciklama.trim() || null,
          hedef_tarih: hedef || null,
        });
      }}
    >
      <FormAlani etiket="Adım" htmlFor={`baslik-${kimlik}`}>
        <Input
          id={`baslik-${kimlik}`}
          value={baslik}
          onChange={(olay) => setBaslik(olay.target.value)}
          required
          maxLength={200}
        />
      </FormAlani>
      <FormAlani
        etiket="Ne olunca tamam sayılır"
        htmlFor={`aciklama-${kimlik}`}
        istegeBagli
      >
        <textarea
          id={`aciklama-${kimlik}`}
          value={aciklama}
          onChange={(olay) => setAciklama(olay.target.value)}
          rows={2}
          maxLength={1000}
          className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
        />
      </FormAlani>
      <FormAlani etiket="Hedef tarih" htmlFor={`hedef-${kimlik}`} istegeBagli>
        <Input
          id={`hedef-${kimlik}`}
          type="date"
          value={hedef}
          onChange={(olay) => setHedef(olay.target.value)}
          className="w-fit"
        />
      </FormAlani>
      <div className="flex gap-3">
        <Button type="submit" size="sm" disabled={bekleniyor || !baslik.trim()}>
          {dugme}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onVazgec}>
          Vazgeç
        </Button>
      </div>
    </form>
  );
}

/* --- Zaman çizelgesi (aktif / tamamlandı) --------------------------------- */

function ZamanCizelgesi({
  detay,
  taraf,
  hitap,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  hitap: Hitap;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const { tamamlanan, toplam, geciken } = detay.ilerleme;
  const eylemVar = taraf !== null && detay.durum === "aktif";

  return (
    <PanelBolumu
      id="cizelge"
      baslik={detay.surec_adi ?? "Zaman çizelgesi"}
      aciklama={`${tamamlanan}/${toplam} adım tamamlandı${
        geciken > 0 ? ` · ${geciken} gecikmiş` : ""
      }. Bir adım, iki taraf da “tamamlandı” deyince tamamlanır.`}
    >
      <ol className={SUREC_CIZGISI}>
        {detay.milestonelar.map((adim) => (
          <CizelgeAdimi
            key={adim.id}
            detay={detay}
            adim={adim}
            taraf={taraf}
            hitap={hitap}
            eylemVar={eylemVar}
            bekleniyor={bekleniyor}
            yap={yap}
          />
        ))}
      </ol>
    </PanelBolumu>
  );
}

function CizelgeAdimi({
  detay,
  adim,
  taraf,
  hitap,
  eylemVar,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  adim: MilestoneYaniti;
  taraf: Taraf | null;
  hitap: Hitap;
  eylemVar: boolean;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const gorunum = adimGorunumu(adim, detay, taraf, hitap);

  return (
    <li className="relative flex flex-col gap-1.5">
      <CizgiNoktasi tamamlandi={gorunum.tamamlandi} />
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-medium text-ana">{adim.baslik}</span>
        <span className="text-xs text-muted-foreground">
          {adim.hedef_tarih
            ? `hedef ${tarihYaz(adim.hedef_tarih)}`
            : "tarihsiz"}
        </span>
        {adim.gecikmis ? <DurumEtiketi metin="Gecikmiş" /> : null}
      </div>
      <AdimMetinleri adim={adim} />
      <p
        className={
          gorunum.siraBende
            ? "text-sm font-medium text-pretty"
            : "text-sm text-pretty"
        }
      >
        {gorunum.metin}
      </p>
      {adim.kanit_linki ? (
        <a
          href={adim.kanit_linki}
          target="_blank"
          rel="noreferrer"
          className="w-fit text-sm break-all text-baglanti underline"
        >
          {adim.kanit_linki}
        </a>
      ) : null}

      {eylemVar && !gorunum.tamamlandi ? (
        <div className="flex flex-wrap items-center gap-3 pt-1">
          {gorunum.benIsaretledim ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={bekleniyor}
              onClick={() =>
                void yap(() => milestoneIsaretiGeriAl(detay.id, adim.id))
              }
            >
              İşaretimi geri al
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              variant={gorunum.siraBende ? "default" : "outline"}
              disabled={bekleniyor}
              onClick={() =>
                void yap(() => milestoneIsaretle(detay.id, adim.id))
              }
            >
              {gorunum.siraBende
                ? "Onayla, tamamlandı"
                : "Tamamlandı olarak işaretle"}
            </Button>
          )}
          <KanitLinki
            detay={detay}
            adim={adim}
            bekleniyor={bekleniyor}
            yap={yap}
          />
        </div>
      ) : null}
    </li>
  );
}

function KanitLinki({
  detay,
  adim,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  adim: MilestoneYaniti;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const [acik, setAcik] = useState(false);
  const [link, setLink] = useState(adim.kanit_linki ?? "");

  if (!acik) {
    return (
      <button
        type="button"
        onClick={() => setAcik(true)}
        className="text-sm text-baglanti underline-offset-4 hover:underline"
      >
        {adim.kanit_linki ? "Kanıt linkini değiştir" : "Kanıt linki ekle"}
      </button>
    );
  }
  return (
    <form
      className="flex w-full flex-wrap items-center gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        void yap(() =>
          milestoneGuncelle(detay.id, adim.id, {
            kanit_linki: link.trim() || null,
          }),
        ).then(() => setAcik(false));
      }}
    >
      <Input
        type="url"
        value={link}
        onChange={(olay) => setLink(olay.target.value)}
        placeholder="https://…"
        aria-label="Kanıt linki"
        className="max-w-sm flex-1"
      />
      <Button type="submit" size="sm" disabled={bekleniyor}>
        Kaydet
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => setAcik(false)}
      >
        Vazgeç
      </Button>
    </form>
  );
}
