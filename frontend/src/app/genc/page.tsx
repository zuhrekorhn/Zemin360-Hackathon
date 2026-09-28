"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { FirsatKarti, IlgiSatiri } from "@/components/firsatlar";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  BosDurum,
  DurumEtiketi,
  IletisimSatiri,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type BanaGelenIlgi,
  type GencEslesmesi,
  type Guclendirme,
  type IsbirligiOzeti,
  banaGelenler,
  eslesmeyiKabulEt,
  eslesmeyiReddet,
  firsatlarim,
  gencIlgi,
  ilgilerim,
  ilgiyiGeriCek,
  isbirliklerim,
  kartGuclendir,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { gencDurumEtiketi } from "@/lib/ilgi";
import { kartTamamlamaCagrisi, profilBandi } from "@/lib/profil";
import { ISBIRLIGI_DURUM_ETIKETLERI, ilerlemeMetni } from "@/lib/takip";
import {
  CALISMA_MODELI_ETIKETLERI,
  DENEYIM_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * Genç paneli (docs/faz-b-kimlik-ve-dongu.md § 7): kartlarım, kanıt
 * bekleyenler, bana gelen ilgiler (kabul et / reddet), iş birliklerim.
 *
 * Kabulden önce kurum gencin e-postasını görmez; kabul edince iki tarafın
 * e-postası açılır ve iş birliği başlar (§ 5).
 *
 * Genç akışı (docs/plans/genc-akisi.md § 7): açık ilan panosu yok. Sana uygun
 * fırsatlar (kendi kartına önerilmiş, eşik üstü ihtiyaçlar), kartını güçlendir
 * (sayılar gerçek skorlardan), ilgilerim. Gencin ilgisi açık onayla gider.
 */

export default function GencPaneli() {
  return (
    <GirisKapisi roller={["genc"]}>
      <GencPaneliIcerigi />
    </GirisKapisi>
  );
}

function GencPaneliIcerigi() {
  const hesap = useGirisliHesap();
  const { tazele } = useOturum();

  const [ilgiler, setIlgiler] = useState<BanaGelenIlgi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[] | null>(
    null,
  );
  const [firsatlar, setFirsatlar] = useState<GencEslesmesi[] | null>(null);
  const [benimIlgilerim, setBenimIlgilerim] = useState<GencEslesmesi[] | null>(
    null,
  );
  const [guclendirmeler, setGuclendirmeler] = useState<
    { kartId: string; satir: Guclendirme }[]
  >([]);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);
  const kartIdleri = hesap.yetenek_kartlari.map((kart) => kart.id).join(",");

  const firsatlariOku = useCallback(async () => {
    const [yeni, benim] = await Promise.all([firsatlarim(), ilgilerim()]);
    setFirsatlar(yeni);
    setBenimIlgilerim(benim);
  }, []);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const idler = kartIdleri ? kartIdleri.split(",") : [];
      const [gelen, acik, guclendir] = await Promise.all([
        banaGelenler(),
        isbirliklerim(),
        Promise.all(
          idler.map(async (kartId) =>
            (await kartGuclendir(kartId)).map((satir) => ({ kartId, satir })),
          ),
        ),
        firsatlariOku(),
      ]);
      setIlgiler(gelen);
      setIsbirlikleri(acik);
      setGuclendirmeler(guclendir.flat());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [kartIdleri, firsatlariOku]);

  async function ilgiGoster(firsat: GencEslesmesi) {
    setHata(null);
    try {
      await gencIlgi(firsat.eslesme_id);
      await firsatlariOku();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  async function ilgiyiCek(ilgi: GencEslesmesi) {
    setHata(null);
    try {
      await ilgiyiGeriCek(ilgi.eslesme_id);
      await firsatlariOku();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function yanitla(ilgi: BanaGelenIlgi, kabul: boolean) {
    setHata(null);
    try {
      const yanit = kabul
        ? await eslesmeyiKabulEt(ilgi.eslesme_id)
        : await eslesmeyiReddet(ilgi.eslesme_id);
      setIlgiler((oncekiler) =>
        (oncekiler ?? []).map((kayit) =>
          kayit.eslesme_id === ilgi.eslesme_id
            ? {
                ...kayit,
                durum: yanit.durum,
                isbirligi_id: yanit.isbirligi_id,
                iletisim: yanit.iletisim,
              }
            : kayit,
        ),
      );
      if (kabul) setIsbirlikleri(await isbirliklerim());
      // İlgi bildirimi okunmuş sayılmaz ama panel güncel /me ister (kartlar).
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  const kartlar = hesap.yetenek_kartlari;
  const bant = profilBandi(hesap);
  const kartCagrisi = kartTamamlamaCagrisi(hesap);
  const kanitBekleyenler = kartlar.filter((kart) => kart.kanit_bekleyen);
  const bekleyenIlgi =
    ilgiler?.filter((ilgi) => ilgi.durum === "ilgileniliyor").length ?? 0;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Merhaba{hesap.ad ? `, ${hesap.ad}` : ""}
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          {bekleyenIlgi > 0
            ? `${bekleyenIlgi} kurum kartınla ilgileniyor ve yanıtını bekliyor.`
            : "Kartların, kanıtların ve sana gelen ilgiler burada."}
        </p>
      </header>

      {kartCagrisi ? (
        // Onaylı kartı olmayan genç eşleştirmeye girmez (plan § 5.2).
        <div className="flex flex-wrap items-center gap-3 rounded-sm border border-baglanti bg-card px-4 py-3">
          <span className="font-medium text-ana">{kartCagrisi}</span>
          <Button asChild size="sm">
            <Link href="/kesif">Kartını oluştur</Link>
          </Button>
        </div>
      ) : null}

      {bant ? (
        // Engellemez: eşleştirme sürer, bant yalnızca eksikleri hatırlatır.
        <div
          role="note"
          className="flex flex-wrap items-center gap-3 rounded-sm border border-kenar bg-muted px-4 py-3 text-sm text-pretty"
        >
          <span>{bant}</span>
          <Link href="/profil" className="text-baglanti underline">
            Profilime git
          </Link>
        </div>
      ) : null}

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {kartlar.length > 0 ? (
        <PanelBolumu
          id="firsatlar"
          baslik="Sana uygun fırsatlar"
          aciklama="Kartına uyan firma ihtiyaçları. İlgilendiğin fırsatı firmaya bildirebilirsin; firma da ilgilenirse iletişim bilgileriniz paylaşılır."
        >
          {firsatlar === null ? (
            <p className="text-sm text-muted-foreground" role="status">
              Yükleniyor…
            </p>
          ) : firsatlar.length === 0 ? (
            <BosDurum
              metin="Şu an sana uygun bir fırsat yok. Kanıt eklemek ve kartını güncel tutmak, yeni fırsatlarda öne çıkmanı sağlar."
              eylem={{ href: `/kart/${kartlar[0].id}`, etiket: "Kartına git" }}
            />
          ) : (
            <ul className="flex flex-col gap-4">
              {firsatlar.map((firsat) => (
                <FirsatKarti
                  key={firsat.eslesme_id}
                  firsat={firsat}
                  onIlgi={() => ilgiGoster(firsat)}
                />
              ))}
            </ul>
          )}
        </PanelBolumu>
      ) : null}

      {guclendirmeler.length > 0 ? (
        <PanelBolumu
          id="guclendir"
          baslik="Kartını güçlendir"
          aciklama="Kanıt eklediğin çalışmalar güven göstergeni güçlendirir."
        >
          <ul className="flex flex-col gap-3">
            {guclendirmeler.map(({ kartId, satir }) => (
              <li
                key={satir.somut_cikti_id}
                className="flex flex-wrap items-center gap-3 rounded-sm border border-kenar px-4 py-3"
              >
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="text-sm font-medium">{satir.baslik}</span>
                  <span className="text-sm text-pretty text-muted-foreground">
                    {satir.metin}
                  </span>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/kart/${kartId}`}>Kanıt ekle</Link>
                </Button>
              </li>
            ))}
          </ul>
        </PanelBolumu>
      ) : null}

      {benimIlgilerim && benimIlgilerim.length > 0 ? (
        <PanelBolumu
          id="ilgilerim"
          baslik="İlgilerim"
          aciklama="İlgi gösterdiğin fırsatlar. Firma yanıt verene kadar ilgini geri çekebilirsin."
        >
          <ul className="flex flex-col gap-4">
            {benimIlgilerim.map((ilgi) => (
              <IlgiSatiri
                key={ilgi.eslesme_id}
                ilgi={ilgi}
                onGeriCek={() => ilgiyiCek(ilgi)}
              />
            ))}
          </ul>
        </PanelBolumu>
      ) : null}

      <PanelBolumu id="kartlar" baslik="Kartlarım">
        {kartlar.length === 0 ? (
          <BosDurum
            metin="Henüz yetenek kartın yok. Keşif Ajanı’yla kısa bir sohbet yap; ne yaptığını birlikte bir karta dönüştürelim."
            eylem={{ href: "/kesif", etiket: "Kart oluştur" }}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {kartlar.map((kart) => (
              <li key={kart.id}>
                <Link
                  href={`/kart/${kart.id}`}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-muted"
                >
                  <span className="font-medium text-ana">{kart.rol_alani}</span>
                  <span className="text-sm text-muted-foreground">
                    {etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}
                  </span>
                  <span className="ml-auto flex gap-2">
                    {kart.kanit_bekleyen ? (
                      <DurumEtiketi metin="Kanıt bekliyor" />
                    ) : null}
                    {!kart.embedding_var ? (
                      <DurumEtiketi metin="Eşleştirmeye hazır değil" />
                    ) : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>

      {kartlar.length > 0 ? (
        <PanelBolumu
          id="kanit"
          baslik="Kanıt bekleyenler"
          aciklama="Kanıtı olmayan çıktı kartı elemez; ama kanıt ve referans eşleşmede kartını öne çıkarır."
        >
          {kanitBekleyenler.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Tüm kartlarının çıktılarında kanıt var.
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {kanitBekleyenler.map((kart) => (
                <li
                  key={kart.id}
                  className="flex flex-wrap items-center gap-3 text-sm"
                >
                  <span>{kart.rol_alani}</span>
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/kart/${kart.id}`}>Kanıt ekle</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </PanelBolumu>
      ) : null}

      <PanelBolumu
        id="ilgiler"
        baslik="Bana gelen ilgiler"
        aciklama="Bir kurum kartınla ilgilendiğinde burada görünür. Kabul edersen e-posta adresleriniz paylaşılır ve iş birliği açılır."
      >
        {ilgiler === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : ilgiler.length === 0 ? (
          <BosDurum
            metin={
              kartlar.length === 0
                ? "İlgiler bir kartın olduğunda gelir. Önce kartını oluştur."
                : "Henüz bir kurum kartınla ilgilenmedi. Bir kurum ilgilendiğinde bildirim alırsın."
            }
            eylem={
              kartlar.length === 0
                ? { href: "/kesif", etiket: "Kart oluştur" }
                : undefined
            }
          />
        ) : (
          <ul className="flex flex-col gap-4">
            {ilgiler.map((ilgi) => (
              <IlgiKaydi
                key={ilgi.eslesme_id}
                ilgi={ilgi}
                onYanit={(kabul) => yanitla(ilgi, kabul)}
              />
            ))}
          </ul>
        )}
      </PanelBolumu>

      <PanelBolumu id="isbirlikleri" baslik="İş birliklerim">
        {isbirlikleri === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : isbirlikleri.length === 0 ? (
          <BosDurum metin="Bir kurumun ilgisini kabul ettiğinde iş birliği burada açılır." />
        ) : (
          <ul className="flex flex-col gap-4">
            {isbirlikleri.map((isbirligi) => (
              <li
                key={isbirligi.isbirligi_id}
                className="flex flex-col gap-2 rounded-sm border border-kenar px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <span className="font-medium text-ana">
                    {isbirligi.kurum_adi}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {tarihYaz(isbirligi.baslangic_tarihi)} tarihinde başladı
                  </span>
                </div>
                <p className="text-sm text-pretty">
                  {isbirligi.problem_tanimi}
                </p>
                <IletisimSatiri
                  iletisim={isbirligi.iletisim}
                  karsiTaraf="kurum"
                />
                <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-2">
                  <DurumEtiketi
                    metin={
                      ISBIRLIGI_DURUM_ETIKETLERI[isbirligi.durum] ??
                      isbirligi.durum
                    }
                    baglanti={isbirligi.durum === "tamamlandi"}
                  />
                  <span className="text-xs text-muted-foreground">
                    {ilerlemeMetni(isbirligi.durum, isbirligi.ilerleme)}
                  </span>
                  <Button
                    asChild
                    size="sm"
                    variant="outline"
                    className="ml-auto"
                  >
                    <Link href={`/isbirligi/${isbirligi.isbirligi_id}`}>
                      {isbirligi.durum === "plan_bekliyor"
                        ? "Planı gör"
                        : "İş birliğini aç"}
                    </Link>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>
    </main>
  );
}

function IlgiKaydi({
  ilgi,
  onYanit,
}: {
  ilgi: BanaGelenIlgi;
  onYanit: (kabul: boolean) => Promise<void>;
}) {
  const ihtiyac = ilgi.ihtiyac_karti;
  const [bekleniyor, setBekleniyor] = useState(false);

  // Çift tıklamayı düğmede de kesiyoruz (backend zaten tekrarı yan etkisiz
  // karşılıyor); hata olursa düğmeler yeniden açılır.
  async function yanitVer(kabul: boolean) {
    setBekleniyor(true);
    try {
      await onYanit(kabul);
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-heading text-lg font-semibold text-ana">
          {ihtiyac.kurum.ad}
        </span>
        <span className="text-xs text-muted-foreground">
          “{ilgi.rol_alani}” kartınla · {tarihYaz(ilgi.son_aktivite_tarihi)}
        </span>
      </div>

      <p className="text-sm text-pretty">{ihtiyac.problem_tanimi}</p>
      {ihtiyac.basari_kriteri ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Başarı ölçütü: {ihtiyac.basari_kriteri}
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        {[
          ihtiyac.sehir_tercihi ? sehirEtiketi(ihtiyac.sehir_tercihi) : null,
          ihtiyac.calisma_modeli
            ? etiketle(CALISMA_MODELI_ETIKETLERI, ihtiyac.calisma_modeli)
            : null,
          ihtiyac.musaitlik_tercihi
            ? etiketle(MUSAITLIK_ETIKETLERI, ihtiyac.musaitlik_tercihi)
            : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>

      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-3">
        {ilgi.durum === "ilgileniliyor" ? (
          <>
            <Button
              type="button"
              size="lg"
              disabled={bekleniyor}
              onClick={() => void yanitVer(true)}
            >
              Kabul et
            </Button>
            <Button
              type="button"
              size="lg"
              variant="outline"
              disabled={bekleniyor}
              onClick={() => void yanitVer(false)}
            >
              Reddet
            </Button>
            <span className="text-xs text-pretty text-muted-foreground">
              Kabul edersen e-posta adresleriniz iki tarafa açılır.
            </span>
          </>
        ) : ilgi.durum === "kabul_edildi" ? (
          <>
            <DurumEtiketi metin={gencDurumEtiketi(ilgi.durum)} baglanti />
            {ilgi.isbirligi_id ? (
              <Link
                href={`/isbirligi/${ilgi.isbirligi_id}`}
                className="text-sm text-baglanti underline"
              >
                İş birliğine git
              </Link>
            ) : null}
          </>
        ) : (
          <DurumEtiketi metin={gencDurumEtiketi(ilgi.durum)} />
        )}
      </div>

      {ilgi.iletisim ? (
        <IletisimSatiri iletisim={ilgi.iletisim} karsiTaraf="kurum" />
      ) : null}
    </li>
  );
}
