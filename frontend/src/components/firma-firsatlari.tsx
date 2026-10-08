"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { useGirisliHesap } from "@/components/giris-kapisi";
import { KismenUygunRozeti } from "@/components/kart";
import { BolumBasligi } from "@/components/genc-paneli";
import { BosDurum, DurumEtiketi, IletisimSatiri } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
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
import { cn } from "@/lib/utils";

/**
 * Firmanın aday olarak gördükleri (docs/kararlar.md F8):
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

      <Bolum
        id="firsatlar"
        baslik="Size uygun iş birliği fırsatları"
        sayi={firsatlar.length}
        aciklama="Firma kartınıza uyan iş birliği fırsatları. İlgilendiğiniz fırsatı ihtiyacın sahibi firmaya bildirebilirsiniz; o da ilgilenirse iletişim bilgileriniz paylaşılır."
      >
        {firsatlar.length === 0 ? (
          <BosDurum metin="Şu an kartınıza uyan bir fırsat yok. Firmalar yeni ihtiyaçlar tanımladıkça burada görünür." />
        ) : (
          <ul className="flex flex-col gap-4">
            {firsatlar.map((firsat) => (
              <FirsatKarti
                key={firsat.eslesme_id}
                firsat={firsat}
                onIlgi={() => yap(() => firmaIlgi(firsat.eslesme_id))}
              />
            ))}
          </ul>
        )}
      </Bolum>

      {gelenler.length > 0 ? (
        <Bolum
          id="gelen-ilgiler"
          baslik="Size gelen ilgiler"
          sayi={gelenler.length}
          aciklama="Bu firmalar iş birliği ihtiyaçları için sizinle ilgileniyor. Kabul ederseniz iletişim bilgileriniz paylaşılır ve iş birliği başlar."
        >
          <ul className="flex flex-col gap-4">
            {gelenler.map((satir) => (
              <IlgiSatiri
                key={satir.eslesme_id}
                satir={satir}
                onKabul={() => yap(() => firmaKabul(satir.eslesme_id))}
                onRed={() => yap(() => firmaRed(satir.eslesme_id))}
              />
            ))}
          </ul>
        </Bolum>
      ) : null}

      {ilgilerimiz.length > 0 ? (
        <Bolum id="ilgilerimiz" baslik="İlgilerimiz">
          <ul className="flex flex-col gap-4">
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
        </Bolum>
      ) : null}
    </>
  );
}

/** Panelin diğer bölümleriyle aynı başlık ve aralık. */
function Bolum({
  id,
  baslik,
  sayi,
  aciklama,
  children,
}: {
  id: string;
  baslik: string;
  sayi?: number;
  aciklama?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      aria-labelledby={`${id}-baslik`}
      className="flex scroll-mt-24 flex-col gap-4"
    >
      <BolumBasligi
        id={`${id}-baslik`}
        baslik={baslik}
        sayi={sayi}
        aciklama={aciklama}
      />
      {children}
    </section>
  );
}

function IlanOzeti({ satir }: { satir: FirmaAdayEslesmesi }) {
  const ilan = satir.ihtiyac_karti;
  return (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="flex flex-wrap items-center gap-2 font-heading text-xl leading-snug font-semibold text-ana">
          {ilan.kurum.ad}
          <DogrulanmisFirma dogrulandi={ilan.kurum.dogrulandi} />
        </span>
        <span className="flex flex-wrap items-center gap-2">
          <KismenUygunRozeti uygunluk={satir.uygunluk} />
          <span className="rounded-full bg-baglanti/10 px-2.5 py-1 text-xs font-medium text-baglanti">
            {uyumMetni(satir.uyum)}
          </span>
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
    <li className={cn(KUTU, "flex flex-col gap-3.5 px-6 py-5")}>
      <IlanOzeti satir={firsat} />
      <section className="flex flex-col gap-1 rounded-lg border-l-[3px] border-baglanti bg-baglanti/[0.06] px-4 py-3">
        <h4 className="font-heading text-sm font-semibold text-ana">
          {NEDEN_UYGUN}
        </h4>
        <p className="text-sm leading-relaxed text-pretty">
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
          <div className="flex flex-col gap-3 rounded-lg bg-muted px-4 py-3">
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
  const hesap = useGirisliHesap();
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
    <li className={cn(KUTU, "flex flex-col gap-3.5 px-6 py-5")}>
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
        <IletisimSatiri
          iletisim={satir.iletisim}
          karsiTaraf="kurum"
          taslak={{
            adayTuru: "firma",
            gonderenAdi: hesap.ad ?? "",
            aliciAdi: satir.ihtiyac_karti.kurum.ad,
            problem: satir.ihtiyac_karti.problem_tanimi,
            basariKriteri: satir.ihtiyac_karti.basari_kriteri,
          }}
        />
      ) : null}
    </li>
  );
}
