"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import {
  BosDurum,
  DurumEtiketi,
  IletisimSatiri,
  PanelBolumu,
} from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type EslesmeDurumYaniti,
  type FirmaAdayEslesmesi,
  firmaEslesmelerim,
  firmaIlgi,
  firmaIlgiyiGeriCek,
  firmaKabul,
  firmaRed,
} from "@/lib/api";
import { isbirligiTuruEtiketi } from "@/lib/firma-karti";
import {
  FIRMA_ILETISIM_ONAYI,
  adayEslesmeleriniAyir,
  adayFirmaDurumEtiketi,
  adayFirmaEylemleri,
} from "@/lib/firma-ilgi";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { ILETISIM_ONAYI_KUTUSU, NEDEN_UYGUN, uyumMetni } from "@/lib/ilgi";

/**
 * Firmanın aday olarak gördükleri (docs/plans/firma-akisi.md § 0 karar 8, § 8):
 * "Size uygun iş birliği fırsatları", "Size gelen ilgiler", "İlgilerimiz".
 * Yalnızca firma kartı olan firmada gösterilir (kartı olmayan aday olamaz).
 * Gencin ana sayfasındaki akışın aynısı; metinler firmaya "siz".
 */
export function FirmaFirsatlari() {
  const [eslesmeler, setEslesmeler] = useState<FirmaAdayEslesmesi[] | null>(
    null,
  );
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setEslesmeler(await firmaEslesmelerim());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function yap(istek: () => Promise<EslesmeDurumYaniti>) {
    setHata(null);
    try {
      await istek();
      await oku();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  if (eslesmeler === null) {
    return hata ? (
      <HataKutusu hata={hata} tekrarDene={() => void oku()} />
    ) : null;
  }
  const { firsatlar, gelenler, ilgilerimiz } =
    adayEslesmeleriniAyir(eslesmeler);

  return (
    <>
      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <PanelBolumu
        id="firsatlar"
        baslik="Size uygun iş birliği fırsatları"
        aciklama="Firma kartınıza uyan iş birliği ilanları. İlgilendiğiniz ilanı açan firmaya bildirebilirsiniz; o da ilgilenirse iletişim bilgileriniz paylaşılır."
      >
        {firsatlar.length === 0 ? (
          <BosDurum metin="Şu an kartınıza uyan bir ilan yok. Yeni ilanlar açıldıkça burada görünür." />
        ) : (
          <ul className="flex flex-col gap-3">
            {firsatlar.map((firsat) => (
              <FirsatKarti
                key={firsat.eslesme_id}
                firsat={firsat}
                onIlgi={() => yap(() => firmaIlgi(firsat.eslesme_id))}
              />
            ))}
          </ul>
        )}
      </PanelBolumu>

      {gelenler.length > 0 ? (
        <PanelBolumu
          id="gelen-ilgiler"
          baslik="Size gelen ilgiler"
          aciklama="Bu firmalar iş birliği ilanları için sizinle ilgileniyor. Kabul ederseniz iletişim bilgileriniz paylaşılır ve iş birliği başlar."
        >
          <ul className="flex flex-col gap-3">
            {gelenler.map((satir) => (
              <IlgiSatiri
                key={satir.eslesme_id}
                satir={satir}
                onKabul={() => yap(() => firmaKabul(satir.eslesme_id))}
                onRed={() => yap(() => firmaRed(satir.eslesme_id))}
              />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}

      {ilgilerimiz.length > 0 ? (
        <PanelBolumu id="ilgilerimiz" baslik="İlgilerimiz">
          <ul className="flex flex-col gap-3">
            {ilgilerimiz.map((satir) => (
              <IlgiSatiri
                key={satir.eslesme_id}
                satir={satir}
                onGeriCek={() =>
                  yap(() => firmaIlgiyiGeriCek(satir.eslesme_id))
                }
              />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}
    </>
  );
}

function IlanOzeti({ satir }: { satir: FirmaAdayEslesmesi }) {
  const ilan = satir.ihtiyac_karti;
  return (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="flex flex-wrap items-center gap-2 font-heading text-lg font-semibold text-ana">
          {ilan.kurum.ad}
          <DogrulanmisFirma dogrulandi={ilan.kurum.dogrulandi} />
        </span>
        <span className="rounded-sm border border-baglanti px-2 py-0.5 text-xs text-baglanti">
          {uyumMetni(satir.uyum)}
        </span>
      </div>
      <p className="text-sm text-pretty">{ilan.problem_tanimi}</p>
      {ilan.basari_kriteri ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Başarı ölçütü: {ilan.basari_kriteri}
        </p>
      ) : null}
      {ilan.isbirligi_turu ? (
        <p className="text-xs text-muted-foreground">
          {isbirligiTuruEtiketi(ilan.isbirligi_turu)}
        </p>
      ) : null}
    </>
  );
}

function FirsatKarti({
  firsat,
  onIlgi,
}: {
  firsat: FirmaAdayEslesmesi;
  onIlgi: () => Promise<void>;
}) {
  const [onayAcik, setOnayAcik] = useState(false);
  const [onaylandi, setOnaylandi] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);

  async function ilet() {
    if (!onaylandi || bekleniyor) return;
    setBekleniyor(true);
    try {
      await onIlgi();
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <IlanOzeti satir={firsat} />
      <section className="flex flex-col gap-1">
        <h4 className="font-heading text-sm font-semibold text-ana">
          {NEDEN_UYGUN}
        </h4>
        <p className="text-sm text-pretty text-muted-foreground">
          {firsat.gerekce_metni ?? "Açıklama henüz hazır değil."}
        </p>
      </section>
      <div className="flex flex-col gap-3 border-t border-kenar pt-3">
        {!onayAcik ? (
          <Button
            type="button"
            size="lg"
            className="w-fit"
            onClick={() => setOnayAcik(true)}
          >
            İlgileniyoruz
          </Button>
        ) : (
          <div className="flex flex-col gap-3 rounded-sm border border-kenar bg-muted px-3 py-3">
            <p className="text-sm text-pretty">{FIRMA_ILETISIM_ONAYI}</p>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={onaylandi}
                onChange={(olay) => setOnaylandi(olay.target.checked)}
                className="accent-ana"
              />
              {ILETISIM_ONAYI_KUTUSU}
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                disabled={!onaylandi || bekleniyor}
                onClick={() => void ilet()}
              >
                {bekleniyor ? "İletiliyor…" : "İlgimizi ilet"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={bekleniyor}
                onClick={() => {
                  setOnayAcik(false);
                  setOnaylandi(false);
                }}
              >
                Vazgeç
              </Button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

/** Gelen ilgi (kabul / şimdilik değil) ya da kendi ilgimiz (geri çek). */
function IlgiSatiri({
  satir,
  onKabul,
  onRed,
  onGeriCek,
}: {
  satir: FirmaAdayEslesmesi;
  onKabul?: () => Promise<void>;
  onRed?: () => Promise<void>;
  onGeriCek?: () => Promise<void>;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const eylemler = adayFirmaEylemleri(satir.durum);

  async function calistir(eylem?: () => Promise<void>) {
    if (!eylem || bekleniyor) return;
    setBekleniyor(true);
    try {
      await eylem();
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <IlanOzeti satir={satir} />
      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-3">
        <DurumEtiketi
          metin={adayFirmaDurumEtiketi(satir.durum)}
          baglanti={satir.durum === "kabul_edildi"}
        />
        {eylemler.kabulVeyaRed && onKabul ? (
          <>
            <Button
              type="button"
              size="sm"
              disabled={bekleniyor}
              onClick={() => void calistir(onKabul)}
            >
              Kabul et
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={bekleniyor}
              onClick={() => void calistir(onRed)}
            >
              Şimdilik değil
            </Button>
          </>
        ) : null}
        {eylemler.geriCek && onGeriCek ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={bekleniyor}
            onClick={() => void calistir(onGeriCek)}
          >
            İlgimizi geri çek
          </Button>
        ) : null}
        {satir.isbirligi_id ? (
          <Link
            href={`/isbirligi/${satir.isbirligi_id}`}
            className="text-sm text-baglanti underline"
          >
            İş birliğine gidin
          </Link>
        ) : null}
      </div>
      {satir.iletisim ? (
        <IletisimSatiri iletisim={satir.iletisim} karsiTaraf="kurum" />
      ) : null}
    </li>
  );
}
