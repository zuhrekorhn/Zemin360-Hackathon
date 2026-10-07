"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { FirmaOnaylari } from "@/components/firma-onaylari";
import { GozlemPaneli } from "@/components/gozlem-paneli";
import { IncelemeKuyrugu } from "@/components/inceleme-kuyrugu";
import { GirisKapisi } from "@/components/giris-kapisi";
import {
  BosDurum,
  DurumEtiketi,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type CanlilikOlayi,
  type GirvakSayilari,
  type PasifBaglanti,
  type ProgramHedefi,
  type TaramaSonucu,
  canlilikOlaylari,
  girvakSayilari,
  pasifBaglantilar,
  taramaCalistir,
} from "@/lib/api";
import {
  alicilarMetni,
  hedefBasligi,
  hedefYuzdesi,
  pasifSureMetni,
  turEtiketi,
} from "@/lib/canlilik";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * GİRVAK paneli (docs/canlilik.md § 7).
 *
 *   1. Program hedefleri — programın kendi adıyla ve platformda neyi
 *      saydığımızla; aradaki fark gizlenmez.
 *   2. Canlılık — "Taramayı şimdi çalıştır" (canlıda aynı işi cron yapar),
 *      şu an pasifleşen bağlantılar, son Canlılık olayları.
 *   3. Platform sayıları.
 * Kişisel veri yalnızca ad; e-posta yok.
 */

export default function GirvakPaneli() {
  return (
    <GirisKapisi roller={["girvak"]}>
      <GirvakSayfasi />
    </GirisKapisi>
  );
}

function GirvakSayfasi() {
  const [sayilar, setSayilar] = useState<GirvakSayilari | null>(null);
  const [pasifler, setPasifler] = useState<PasifBaglanti[] | null>(null);
  const [olaylar, setOlaylar] = useState<CanlilikOlayi[] | null>(null);
  const [tarama, setTarama] = useState<TaramaSonucu | null>(null);
  const [taraniyor, setTaraniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [s, p, o] = await Promise.all([
        girvakSayilari(),
        pasifBaglantilar(),
        canlilikOlaylari(),
      ]);
      setSayilar(s);
      setPasifler(p);
      setOlaylar(o);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function taramayiCalistir() {
    setHata(null);
    setTaraniyor(true);
    try {
      setTarama(await taramaCalistir());
      await oku();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setTaraniyor(false);
    }
  }

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="GİRVAK paneli"
        aciklama="Program hedefleri gerçek sayılarla, pasifleşen bağlantılar ve son hatırlatmalar. Kişisel bilgi olarak yalnızca ad görünür."
      />

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {sayilar === null && !hata ? (
        <p className="text-sm text-muted-foreground" role="status">
          Yükleniyor…
        </p>
      ) : null}

      {sayilar ? (
        <PanelBolumu
          id="hedefler"
          baslik="Program hedefleri"
          aciklama="Her hedefin altında platformda neyi saydığımız yazıyor; programın tanımıyla bizim ölçümümüz birebir aynı olmayabilir."
        >
          <ul className="flex flex-col gap-5">
            {sayilar.hedefler.map((hedef) => (
              <HedefSatiri key={hedef.anahtar} hedef={hedef} />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}

      <PanelBolumu
        id="canlilik"
        baslik="Canlılık taraması"
        aciklama="Hareketsiz kalan öneri, ilgi, plan ve adımlar için ilgili kişiye bir hatırlatma bırakır; aynı dönemde aynı hatırlatmayı tekrarlamaz. Canlıda bu işi zamanlanmış görev günde iki kez yapar."
      >
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            size="lg"
            disabled={taraniyor}
            onClick={() => void taramayiCalistir()}
          >
            {taraniyor ? "Taranıyor…" : "Taramayı şimdi çalıştır"}
          </Button>
          {tarama ? <TaramaOzeti sonuc={tarama} /> : null}
        </div>
      </PanelBolumu>

      <FirmaOnaylari />

      <IncelemeKuyrugu />

      <GozlemPaneli />

      <PanelBolumu
        id="pasifler"
        baslik="Pasifleşen bağlantılar"
        aciklama="Şu an hareketsizlik süresini aşmış kayıtlar; en uzun süredir hareketsiz olan önce. Bu liste okunurken hiçbir hatırlatma gönderilmez."
      >
        {pasifler === null ? null : pasifler.length === 0 ? (
          <BosDurum metin="Şu an hareketsizlik süresini aşmış bir bağlantı yok." />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {pasifler.map((pasif) => (
              <PasifSatiri
                key={`${pasif.eslesme_id}-${pasif.tur}-${pasif.adim ?? ""}`}
                pasif={pasif}
              />
            ))}
          </ul>
        )}
      </PanelBolumu>

      <PanelBolumu id="olaylar" baslik="Son hatırlatmalar">
        {olaylar === null ? null : olaylar.length === 0 ? (
          <BosDurum metin="Henüz hatırlatma gönderilmedi. Tarama çalıştığında burada görünür." />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {olaylar.map((olay) => (
              <li key={olay.id} className="flex flex-col gap-1 px-4 py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <DurumEtiketi metin={turEtiketi(olay.tur)} />
                  <span className="text-sm">
                    {olay.alici_adi ?? "—"}
                    {olay.alici_rol ? (
                      <span className="text-muted-foreground">
                        {" "}
                        ({olay.alici_rol === "genc" ? "genç" : "firma"})
                      </span>
                    ) : null}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {tarihYaz(olay.tetiklenme_tarihi, true)}
                  </span>
                </div>
                {olay.mesaj_metni ? (
                  <p className="text-sm text-pretty text-muted-foreground">
                    {olay.mesaj_metni}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>

      {sayilar ? (
        <>
          <PanelBolumu baslik="Hesaplar ve kartlar">
            <SayiIzgarasi
              ogeler={[
                { etiket: "Genç hesabı", sayi: sayilar.hesap.genc },
                { etiket: "Firma hesabı", sayi: sayilar.hesap.kurum },
                { etiket: "Yetenek kartı", sayi: sayilar.yetenek_karti },
                { etiket: "İhtiyaç kartı", sayi: sayilar.ihtiyac_karti },
              ]}
            />
          </PanelBolumu>

          <PanelBolumu
            baslik="Eşleşmeler ve iş birlikleri"
            aciklama="Öneriden tamamlanan iş birliğine: firma ilgilenir, genç kabul eder, plan iki tarafça onaylanır ve adım adım tamamlanır."
          >
            <SayiIzgarasi
              ogeler={[
                { etiket: "Önerildi", sayi: sayilar.eslesme.onerildi },
                {
                  etiket: "Gencin yanıtı bekleniyor",
                  sayi: sayilar.eslesme.ilgileniliyor,
                },
                { etiket: "Kabul edildi", sayi: sayilar.eslesme.kabul_edildi },
                { etiket: "Reddedildi", sayi: sayilar.eslesme.reddedildi },
                { etiket: "İş birliği", sayi: sayilar.isbirligi },
                {
                  etiket: "Planı bekleyen",
                  sayi: sayilar.isbirligi_durumlari.plan_bekliyor,
                },
                {
                  etiket: "Süren iş birliği",
                  sayi: sayilar.isbirligi_durumlari.aktif,
                },
                {
                  etiket: "Tamamlanan iş birliği",
                  sayi: sayilar.isbirligi_durumlari.tamamlandi,
                },
              ]}
            />
          </PanelBolumu>

          <PanelBolumu
            baslik="Genç–firma ve firma–firma"
            aciklama="Yukarıdaki toplamların eşleşme türüne göre dağılımı. Firma–firma, bir firmanın iş birliği ortağı aradığı ihtiyaçlardan çıkan eşleşmeler."
          >
            <SayiIzgarasi
              ogeler={[
                {
                  etiket: "Genç–firma karşılıklı ilgi",
                  sayi: sayilar.kirilim.genc_firma.karsilikli_ilgi,
                },
                {
                  etiket: "Genç–firma iş birliği",
                  sayi: sayilar.kirilim.genc_firma.isbirligi,
                },
                {
                  etiket: "Genç–firma tamamlanan",
                  sayi: sayilar.kirilim.genc_firma.tamamlanan,
                },
                {
                  etiket: "Firma–firma öneri",
                  sayi: sayilar.kirilim.firma_firma.oneri,
                },
                {
                  etiket: "Firma–firma karşılıklı ilgi",
                  sayi: sayilar.kirilim.firma_firma.karsilikli_ilgi,
                },
                {
                  etiket: "Firma–firma iş birliği",
                  sayi: sayilar.kirilim.firma_firma.isbirligi,
                },
                {
                  etiket: "Firma–firma tamamlanan",
                  sayi: sayilar.kirilim.firma_firma.tamamlanan,
                },
              ]}
            />
          </PanelBolumu>

          <PanelBolumu
            baslik="Kapanan ihtiyaçlar"
            aciklama="Firmaların ihtiyacı kapatırken seçtiği neden. Nedeni yalnızca siz görürsünüz."
          >
            <SayiIzgarasi
              ogeler={[
                {
                  etiket: "Platformda bulundu",
                  sayi: sayilar.kapanan_ihtiyaclar.platformda_bulundu,
                },
                {
                  etiket: "Başka yoldan bulundu",
                  sayi: sayilar.kapanan_ihtiyaclar.baska_yoldan_bulundu,
                },
                {
                  etiket: "Vazgeçildi",
                  sayi: sayilar.kapanan_ihtiyaclar.vazgecildi,
                },
                {
                  etiket: "Yanlış girildi",
                  sayi: sayilar.kapanan_ihtiyaclar.hatali_girildi,
                },
              ]}
            />
          </PanelBolumu>
        </>
      ) : null}
    </Sayfa>
  );
}

/** Hedef: programın adıyla başlık, altında bizim ölçümümüz, ince ilerleme çizgisi. */
function HedefSatiri({ hedef }: { hedef: ProgramHedefi }) {
  const yuzde = hedefYuzdesi(hedef.sayi, hedef.hedef);
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <span className="font-medium text-ana">
          {hedefBasligi(hedef.hedef, hedef.program_adi)}
        </span>
        <span className="font-mono text-sm text-ana">
          {hedef.sayi} / {hedef.hedef}
        </span>
      </div>
      <span className="text-xs text-pretty text-muted-foreground">
        Platformda: {hedef.olcum}
      </span>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-kenar"
        role="progressbar"
        aria-valuenow={hedef.sayi}
        aria-valuemin={0}
        aria-valuemax={hedef.hedef}
        aria-label={hedefBasligi(hedef.hedef, hedef.program_adi)}
      >
        <div className="h-full bg-baglanti" style={{ width: `${yuzde}%` }} />
      </div>
    </li>
  );
}

function TaramaOzeti({ sonuc }: { sonuc: TaramaSonucu }) {
  const turler = Object.entries(sonuc.olaylar);
  return (
    <p className="text-sm text-pretty" role="status">
      {turler.length === 0
        ? "Yeni hatırlatma yok: hareketsizlik süresini aşan kayıt yok ya da bu dönemde zaten hatırlatıldı."
        : `${sonuc.bildirim} bildirim gönderildi. ${turler
            .map(([tur, sayi]) => `${turEtiketi(tur)}: ${sayi}`)
            .join(", ")}.`}
      <span className="ml-1 text-xs text-muted-foreground">
        ({sonuc.sure_sn} sn)
      </span>
    </p>
  );
}

function PasifSatiri({ pasif }: { pasif: PasifBaglanti }) {
  return (
    <li className="flex flex-col gap-1 px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <DurumEtiketi metin={turEtiketi(pasif.tur)} />
        <span className="text-sm">
          {pasif.genc_adi} · {pasif.kurum_adi}
        </span>
        {pasif.isbirligi_id ? (
          <Link
            href={`/isbirligi/${pasif.isbirligi_id}`}
            className="ml-auto text-sm text-baglanti underline"
          >
            İş birliğini aç
          </Link>
        ) : null}
      </div>
      <p className="text-sm text-pretty text-muted-foreground">
        {pasifSureMetni(pasif.tur, pasif.gun)}
        {pasif.adim ? ` · “${pasif.adim}”` : ""} · hatırlatılacak:{" "}
        {alicilarMetni(pasif.alicilar)} ·{" "}
        {pasif.son_hatirlatma
          ? `son hatırlatma ${tarihYaz(pasif.son_hatirlatma, true)}`
          : "henüz hatırlatılmadı"}
      </p>
    </li>
  );
}

/** Hairline ızgara — doğrulama göstergesiyle aynı "belge" dili. */
function SayiIzgarasi({
  ogeler,
}: {
  ogeler: { etiket: string; sayi: number }[];
}) {
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-kenar bg-kenar sm:grid-cols-3">
      {ogeler.map((oge) => (
        <div key={oge.etiket} className="flex flex-col gap-1 bg-card px-4 py-3">
          <dt className="text-xs text-muted-foreground">{oge.etiket}</dt>
          <dd className="font-mono text-2xl text-ana">{oge.sayi}</dd>
        </div>
      ))}
    </dl>
  );
}
