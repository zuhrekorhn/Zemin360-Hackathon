"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  DurumEtiketi,
  IletisimSatiri,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type IsbirligiDetayi,
  type MilestoneGirdisi,
  type MilestoneYaniti,
  isbirligiGetir,
  milestoneEkle,
  milestoneGuncelle,
  milestoneIsaretiGeriAl,
  milestoneIsaretle,
  milestoneSil,
  planOner,
  planOnayla,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  ISBIRLIGI_DURUM_ETIKETLERI,
  type Taraf,
  adimGorunumu,
  planOnayGorunumu,
  tarafim,
} from "@/lib/takip";
import { panelYolu } from "@/lib/yonlendirme";

/**
 * İş birliği sayfası — Takip Ajanı (docs/faz-c-takip.md § 8).
 *
 * İki tarafa aynı sayfa. Üç hâl:
 *   plan_bekliyor — ajanın önerdiği plan düzenlenir, iki taraf onaylar;
 *   aktif         — adımlar iki taraflı işaretlenir, gecikme görünür;
 *   tamamlandi    — son adımla kendiliğinden; gencin kartına pilot sinyali.
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
  const taraf = tarafim(hesap.rol);

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
    return (
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-10 sm:px-6 sm:py-16">
        {hata ? (
          <HataKutusu hata={hata} tekrarDene={() => void oku()} />
        ) : (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        )}
      </main>
    );
  }

  const karsiTaraf: Taraf | null =
    taraf === "genc" ? "kurum" : taraf === "kurum" ? "genc" : null;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
            {detay.kurum_adi} · {detay.genc_adi}
          </h1>
          <DurumEtiketi
            metin={ISBIRLIGI_DURUM_ETIKETLERI[detay.durum] ?? detay.durum}
            baglanti={detay.durum === "tamamlandi"}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {detay.rol_alani} · {tarihYaz(detay.baslangic_tarihi)} tarihinde
          başladı
        </p>
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
      </header>

      {detay.durum === "tamamlandi" ? (
        <TamamlandiBandi detay={detay} taraf={taraf} />
      ) : null}

      {detay.durum_ozeti ? (
        <section className="flex flex-col gap-1 rounded-sm border border-kenar bg-card px-4 py-3">
          <span className="text-xs text-muted-foreground">
            Takip Ajanı’nın özeti · {tarihYaz(detay.ozet_tarihi, true)}
          </span>
          <p className="text-sm text-pretty">{detay.durum_ozeti}</p>
        </section>
      ) : null}

      {hata ? <HataKutusu hata={hata} /> : null}

      {detay.durum === "plan_bekliyor" ? (
        <PlanTaslagi
          detay={detay}
          taraf={taraf}
          bekleniyor={bekleniyor}
          planBekleniyor={planBekleniyor && beklemeSayisi < PLAN_BEKLEME_EN_COK}
          yap={yap}
        />
      ) : (
        <ZamanCizelgesi
          detay={detay}
          taraf={taraf}
          bekleniyor={bekleniyor}
          yap={yap}
        />
      )}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href={panelYolu(hesap.rol)}>Panele dön</Link>
        </Button>
      </footer>
    </main>
  );
}

type Yap = (eylem: () => Promise<IsbirligiDetayi>) => Promise<void>;

/* --- Tamamlandı ----------------------------------------------------------- */

function TamamlandiBandi({
  detay,
  taraf,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
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
          Kartına tamamlanmış pilot olarak eklendi; bundan sonraki eşleşmelerde
          öne çıkarır.{" "}
          <Link
            href={`/kart/${detay.yetenek_karti_id}`}
            className="text-baglanti underline"
          >
            Kartını gör
          </Link>
        </p>
      ) : null}
    </section>
  );
}

/* --- Plan taslağı --------------------------------------------------------- */

function PlanTaslagi({
  detay,
  taraf,
  bekleniyor,
  planBekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  bekleniyor: boolean;
  planBekleniyor: boolean;
  yap: Yap;
}) {
  const onay = planOnayGorunumu(detay, taraf);
  const adimlar = detay.milestonelar;

  return (
    <PanelBolumu
      id="plan"
      baslik="Plan"
      aciklama="Takip Ajanı başarı ölçütünden bir plan önerir; iki taraf düzenleyip onaylar. Onaylanan plan değiştirilemez."
    >
      <p className="text-sm text-pretty">{onay.metin}</p>

      {adimlar.length === 0 ? (
        <div className="flex flex-col items-start gap-3 rounded-sm border border-dashed border-kenar px-5 py-4">
          <p className="text-sm text-pretty text-muted-foreground">
            {planBekleniyor
              ? "Takip Ajanı planı hazırlıyor…"
              : "Henüz plan yok. Ajandan plan isteyebilir ya da adımları kendin ekleyebilirsin."}
          </p>
          {taraf ? (
            <Button
              type="button"
              size="lg"
              disabled={bekleniyor}
              onClick={() => void yap(() => planOner(detay.id))}
            >
              {bekleniyor ? "Plan hazırlanıyor…" : "Ajandan plan iste"}
            </Button>
          ) : null}
        </div>
      ) : (
        <ol className="flex flex-col gap-3">
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
              {onay.benOnayladim ? "Planı onayladın" : "Planı onayla"}
            </Button>
            {adimlar.length > 0 ? (
              <Button
                type="button"
                size="lg"
                variant="outline"
                disabled={bekleniyor}
                onClick={() => {
                  if (
                    window.confirm(
                      "Ajan yeni bir plan önerecek; mevcut adımlar silinir ve iki onay da sıfırlanır. Devam edilsin mi?",
                    )
                  ) {
                    void yap(() => planOner(detay.id));
                  }
                }}
              >
                Ajandan yeniden öner
              </Button>
            ) : null}
          </div>
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
      <li className="rounded-sm border border-kenar bg-card px-4 py-3">
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
    <li className="flex flex-col gap-1 rounded-sm border border-kenar bg-card px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-mono text-xs text-muted-foreground">
          {adim.sira + 1}
        </span>
        <span className="font-medium text-ana">{adim.baslik}</span>
        <span className="text-xs text-muted-foreground">
          {adim.hedef_tarih
            ? `hedef ${tarihYaz(adim.hedef_tarih)}`
            : "tarihsiz"}
        </span>
      </div>
      {adim.aciklama ? (
        <p className="text-sm text-pretty text-muted-foreground">
          {adim.aciklama}
        </p>
      ) : null}
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
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const { tamamlanan, toplam, geciken } = detay.ilerleme;
  const eylemVar = taraf !== null && detay.durum === "aktif";

  return (
    <PanelBolumu
      id="cizelge"
      baslik="Zaman çizelgesi"
      aciklama={`${tamamlanan}/${toplam} adım tamamlandı${
        geciken > 0 ? ` · ${geciken} gecikmiş` : ""
      }. Bir adım, iki taraf da “tamamlandı” deyince tamamlanır.`}
    >
      <ol className="relative flex flex-col gap-5 border-l border-kenar pl-5">
        {detay.milestonelar.map((adim) => (
          <CizelgeAdimi
            key={adim.id}
            detay={detay}
            adim={adim}
            taraf={taraf}
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
  eylemVar,
  bekleniyor,
  yap,
}: {
  detay: IsbirligiDetayi;
  adim: MilestoneYaniti;
  taraf: Taraf | null;
  eylemVar: boolean;
  bekleniyor: boolean;
  yap: Yap;
}) {
  const gorunum = adimGorunumu(adim, detay, taraf);

  return (
    <li className="relative flex flex-col gap-1.5">
      <span
        aria-hidden="true"
        className={
          gorunum.tamamlandi
            ? "absolute top-1.5 -left-[25px] size-2.5 rounded-full bg-baglanti"
            : "absolute top-1.5 -left-[25px] size-2.5 rounded-full border border-kenar bg-zemin"
        }
      />
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-medium text-ana">{adim.baslik}</span>
        <span className="text-xs text-muted-foreground">
          {adim.hedef_tarih
            ? `hedef ${tarihYaz(adim.hedef_tarih)}`
            : "tarihsiz"}
        </span>
        {adim.gecikmis ? <DurumEtiketi metin="Gecikmiş" /> : null}
      </div>
      {adim.aciklama ? (
        <p className="text-sm text-pretty text-muted-foreground">
          {adim.aciklama}
        </p>
      ) : null}
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
