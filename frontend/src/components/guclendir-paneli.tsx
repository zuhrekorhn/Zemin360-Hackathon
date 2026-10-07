"use client";

import { Check, Upload } from "lucide-react";
import { useState } from "react";

import {
  Degerlendirme,
  DogrulanamadiEtiketi,
} from "@/components/degerlendirme";
import {
  DosyaEkleFormu,
  DosyaSatiri,
  KanitSatiri,
  LinkEkleFormu,
  indir,
} from "@/components/kanit";
import {
  SIFIRLAMA_ONAYI,
  YENIDEN_DEGERLENDIRME_NOTU,
} from "@/components/kart-duzenleme";
import { OnayAlani } from "@/components/onay-alani";
import { ReferansFormu, ReferansSatiri } from "@/components/referans-parcalari";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { YanPanel } from "@/components/ui/yan-panel";
import { KUTU } from "@/components/ui/yuzey";
import {
  type KanitDurumu,
  type SomutCiktiYaniti,
  type YetenekKartiYaniti,
  dosyaGorunurlugu,
  isKalemiGuncelle,
  itirazEt,
  kalemiDegerlendir,
  kanitDosyasiEkle,
  kanitLinkiEkle,
  kanitParcasiSil,
  referansGeriCek,
  referansIste,
  referansYenidenIste,
} from "@/lib/api";
import { type AdimTuru, type Eksik, eksikler } from "@/lib/calisma";
import { baslikGosterimi, notuBasliklaraAyir } from "@/lib/guven-gostergesi";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { degerlendirildiMi, dosyaParcalari, kanitLinkleri } from "@/lib/kanit";
import { cn } from "@/lib/utils";

/**
 * "Güçlendir" paneli (docs/kararlar.md G18): bir çalışmanın bütün eksikleri
 * numaralı adımlar halinde tek yerde. Eksik adımlar yapılacak sırayla üstte
 * (lib/calisma.ts), tamamlananlar onay işaretiyle altta. Her adımın altında
 * değerlendirmenin o başlık için yazdığı not. Kanıt ve referans eylemleri
 * çalışmayı hemen yeniden değerlendirir; sonuç ve pay metni değişirse gösterge
 * sıfırlanıp yeniden hesaplanır (önce sorulur, eski referans yanıtı geçmişte kalır, G8).
 */

const SIRA: AdimTuru[] = ["kanit", "sonuc", "rol", "referans"];
const BASLIK: Record<AdimTuru, "Kanıt" | "Sonuç" | "Rol" | "Referans"> = {
  kanit: "Kanıt",
  sonuc: "Sonuç",
  rol: "Rol",
  referans: "Referans",
};
const ALAN = {
  kanit: "kanit_orijinalligi",
  sonuc: "sonuc_olculebilirligi",
  rol: "rol_netligi",
  referans: "ucuncu_taraf_onayi",
} as const;
const TAMAM_BASLIGI: Record<AdimTuru, string> = {
  kanit: "Kanıt tamam",
  sonuc: "Sonuç tamam",
  rol: "Payın tamam",
  referans: "Referans tamam",
};

export function GuclendirPaneli({
  acik,
  onKapat,
  kartId,
  cikti,
  durum,
  onDurum,
  onGuncel,
  onHata,
}: {
  acik: boolean;
  onKapat: () => void;
  kartId: string;
  cikti: SomutCiktiYaniti;
  durum: KanitDurumu | undefined;
  onDurum: (durum: KanitDurumu) => void;
  onGuncel: (kart: YetenekKartiYaniti, not?: string) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const [panelHatasi, setPanelHatasi] = useState<Hata | null>(null);
  const parcalar = durum?.kanitlar ?? cikti.kanitlar;
  const linkler = kanitLinkleri(parcalar);
  const dosyalar = dosyaParcalari(parcalar);
  const referanslar = durum?.referanslar ?? [];
  const skor = durum?.guven_skoru ?? cikti.guven_skoru;
  const liste = eksikler({
    kanitSayisi: linkler.length + dosyalar.length,
    referansSayisi: referanslar.length,
    skor,
  });
  const notlar = Object.fromEntries(
    notuBasliklaraAyir(skor?.gerekce_metni).map((p) => [p.baslik, p.metin]),
  );
  const eksikTurler = liste.map((e) => e.tur);
  const sirali = [
    ...liste.map((e) => e.tur),
    ...SIRA.filter((tur) => !eksikTurler.includes(tur)),
  ];
  const tamamlar = SIRA.filter(
    (tur) => !eksikTurler.includes(tur) && (skor?.[ALAN[tur]] ?? null) !== null,
  );

  /** Kanıt ya da referans eylemi; başarılıysa true. */
  async function calistir(is: () => Promise<KanitDurumu>): Promise<boolean> {
    setPanelHatasi(null);
    onHata(null);
    setBekleniyor(true);
    try {
      onDurum(await is());
      return true;
    } catch (sebep) {
      setPanelHatasi(hatayaCevir(sebep));
      return false;
    } finally {
      setBekleniyor(false);
    }
  }

  const alt =
    liste.length === 0
      ? skor
        ? "Eksik yok"
        : "Henüz değerlendirilmedi"
      : [
          `${liste.length} adım kaldı`,
          ...tamamlar.map((tur) => TAMAM_BASLIGI[tur]),
        ].join(" · ");

  return (
    <YanPanel
      acik={acik}
      onKapat={onKapat}
      ust="Çalışmayı güçlendir"
      baslik={cikti.baslik}
      alt={alt}
      etek={
        <>
          <span className="text-xs text-pretty text-muted-foreground">
            Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir; referans
            puanını referans kişi verir.
          </span>
          <Button type="button" variant="outline" onClick={onKapat}>
            Kapat
          </Button>
        </>
      }
    >
      {durum?.dogrulanamadi ? (
        <DogrulanamadiEtiketi notlar={durum.girvak_notlari} />
      ) : null}
      {panelHatasi ? (
        <p role="alert" className="text-sm text-destructive">
          {panelHatasi.metin}
        </p>
      ) : null}

      <ol className="flex flex-col gap-3">
        {sirali.map((tur, i) => {
          const eksik = liste.find((e) => e.tur === tur) ?? null;
          const deger = skor?.[ALAN[tur]] ?? null;
          return (
            <Adim
              key={tur}
              sira={i + 1}
              tur={tur}
              eksik={eksik}
              etiket={baslikGosterimi(BASLIK[tur], deger).metin}
              not={notlar[BASLIK[tur]] ?? null}
            >
              {tur === "kanit" ? (
                <KanitAdimi
                  eksik={eksik}
                  bekleniyor={bekleniyor}
                  degerlendirilmedi={
                    linkler.length + dosyalar.length > 0 &&
                    Boolean(durum) &&
                    !degerlendirildiMi(durum?.guven_skoru)
                  }
                  linkler={linkler}
                  dosyalar={dosyalar}
                  ciktiId={cikti.id}
                  calistir={calistir}
                  onHata={onHata}
                />
              ) : tur === "referans" ? (
                <ReferansAdimi
                  eksik={eksik}
                  ciktiId={cikti.id}
                  referanslar={referanslar}
                  bekleniyor={bekleniyor}
                  calistir={calistir}
                />
              ) : (
                <MetinAdimi
                  tur={tur}
                  eksik={eksik}
                  kartId={kartId}
                  cikti={cikti}
                  referansVar={referanslar.length > 0}
                  onGuncel={onGuncel}
                  onHata={setPanelHatasi}
                />
              )}
            </Adim>
          );
        })}
      </ol>

      {degerlendirildiMi(skor) || durum?.dogrulanamadi ? (
        <div className={cn(KUTU, "px-4 py-3")}>
          {/* Notlar adımların içinde; burada yalnızca itiraz. */}
          <Degerlendirme
            kimlik={cikti.id}
            not={null}
            incelemeBekliyor={durum?.inceleme_bekliyor ?? false}
            kararaItiraz={durum?.dogrulanamadi ?? false}
            bekleniyor={bekleniyor}
            onItiraz={(aciklama) =>
              calistir(() => itirazEt(cikti.id, aciklama))
            }
          />
        </div>
      ) : null}
    </YanPanel>
  );
}

function Adim({
  sira,
  tur,
  eksik,
  etiket,
  not,
  children,
}: {
  sira: number;
  tur: AdimTuru;
  eksik: Eksik | null;
  /** Göstergedeki kelime: "Eksik", "Güçlü", "—". */
  etiket: string;
  not: string | null;
  children: React.ReactNode;
}) {
  const [acik, setAcik] = useState(false);
  const tamam = eksik === null;
  return (
    <li
      className={cn(
        KUTU,
        "flex flex-col gap-3 px-4 py-4",
        tamam && "border-baglanti/30 bg-baglanti/[0.05] shadow-none",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className={cn(
            "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            tamam ? "bg-baglanti text-zemin" : "border border-vurgu text-ana",
          )}
        >
          {tamam ? <Check className="size-3.5" /> : sira}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-sm font-semibold text-metin">
              {eksik ? eksik.kisa : TAMAM_BASLIGI[tur]}
            </h3>
            <span
              className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-xs",
                tamam
                  ? "bg-baglanti/10 text-baglanti"
                  : "bg-vurgu/15 text-metin",
              )}
            >
              {BASLIK[tur]} · {etiket}
            </span>
          </div>
          {not || eksik ? (
            <p className="text-sm text-pretty text-muted-foreground">
              {not ?? eksik?.metin}
            </p>
          ) : null}
        </div>
      </div>
      {tamam ? (
        acik ? (
          <div className="pl-9">{children}</div>
        ) : (
          <button
            type="button"
            onClick={() => setAcik(true)}
            className="ml-9 w-fit text-sm text-baglanti underline underline-offset-4"
          >
            {tur === "referans" ? "Referansları gör" : "Ayrıntıyı gör"}
          </button>
        )
      ) : (
        <div className="pl-9">{children}</div>
      )}
    </li>
  );
}

type Calistir = (is: () => Promise<KanitDurumu>) => Promise<boolean>;

function KanitAdimi({
  eksik,
  bekleniyor,
  degerlendirilmedi,
  linkler,
  dosyalar,
  ciktiId,
  calistir,
  onHata,
}: {
  eksik: Eksik | null;
  bekleniyor: boolean;
  degerlendirilmedi: boolean;
  linkler: ReturnType<typeof kanitLinkleri>;
  dosyalar: ReturnType<typeof dosyaParcalari>;
  ciktiId: string;
  calistir: Calistir;
  onHata: (hata: Hata | null) => void;
}) {
  const [dosyaAcik, setDosyaAcik] = useState(false);
  const [linkAcik, setLinkAcik] = useState(eksik !== null);
  return (
    <div className="flex flex-col gap-3">
      {linkler.length + dosyalar.length > 0 ? (
        <ul className="flex flex-col gap-2.5">
          {linkler.map((parca) => (
            <KanitSatiri
              key={parca.id}
              parca={parca}
              bekleniyor={bekleniyor}
              onKaldir={() =>
                calistir(() => kanitParcasiSil(ciktiId, parca.id))
              }
            />
          ))}
          {dosyalar.map((parca) => (
            <DosyaSatiri
              key={parca.id}
              parca={parca}
              bekleniyor={bekleniyor}
              onIndir={() => indir(ciktiId, parca.id, onHata)}
              onGorunurluk={(gorunur) =>
                calistir(() => dosyaGorunurlugu(ciktiId, parca.id, gorunur))
              }
              onKaldir={() =>
                calistir(() => kanitParcasiSil(ciktiId, parca.id))
              }
            />
          ))}
        </ul>
      ) : null}

      {degerlendirilmedi ? (
        <Button
          type="button"
          size="sm"
          className="w-fit"
          disabled={bekleniyor}
          onClick={() => void calistir(() => kalemiDegerlendir(ciktiId))}
        >
          {bekleniyor ? "Değerlendiriliyor…" : "Bu kanıtı değerlendir"}
        </Button>
      ) : null}

      {linkAcik ? (
        <LinkEkleFormu
          kimlik={ciktiId}
          bekleniyor={bekleniyor}
          onEkle={(url) => calistir(() => kanitLinkiEkle(ciktiId, url))}
        />
      ) : null}
      {dosyaAcik ? (
        <div className="rounded-lg border border-kenar bg-card px-3 py-3">
          <DosyaEkleFormu
            kimlik={ciktiId}
            bekleniyor={bekleniyor}
            onEkle={(dosya) =>
              calistir(() => kanitDosyasiEkle(ciktiId, dosya)).then((tamam) => {
                if (tamam) setDosyaAcik(false);
                return tamam;
              })
            }
            onVazgec={() => setDosyaAcik(false)}
          />
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {!linkAcik ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setLinkAcik(true)}
          >
            Link ekle
          </Button>
        ) : null}
        {!dosyaAcik ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setDosyaAcik(true)}
          >
            <Upload aria-hidden="true" />
            PDF ya da görsel yükle
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function ReferansAdimi({
  eksik,
  ciktiId,
  referanslar,
  bekleniyor,
  calistir,
}: {
  eksik: Eksik | null;
  ciktiId: string;
  referanslar: KanitDurumu["referanslar"];
  bekleniyor: boolean;
  calistir: Calistir;
}) {
  const [formAcik, setFormAcik] = useState(eksik !== null);
  return (
    <div className="flex flex-col gap-3">
      {referanslar.map((referans) => (
        <ReferansSatiri
          key={referans.id}
          referans={referans}
          onYenidenIste={() =>
            void calistir(() => referansYenidenIste(referans.id))
          }
          onGeriCek={() => void calistir(() => referansGeriCek(referans.id))}
        />
      ))}
      {formAcik ? (
        <ReferansFormu
          kimlik={ciktiId}
          bekleniyor={bekleniyor}
          onIste={(eposta) =>
            calistir(() => referansIste(ciktiId, eposta)).then((tamam) => {
              if (tamam && eksik === null) setFormAcik(false);
              return tamam;
            })
          }
          onVazgec={eksik ? undefined : () => setFormAcik(false)}
        />
      ) : (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-fit"
          onClick={() => setFormAcik(true)}
        >
          Bir referans daha iste
        </Button>
      )}
    </div>
  );
}

/** Sonuç ya da pay: çalışmanın metni; kaydedince çalışma yeniden değerlendirilir. */
function MetinAdimi({
  tur,
  eksik,
  kartId,
  cikti,
  referansVar,
  onGuncel,
  onHata,
}: {
  tur: "sonuc" | "rol";
  eksik: Eksik | null;
  kartId: string;
  cikti: SomutCiktiYaniti;
  referansVar: boolean;
  onGuncel: (kart: YetenekKartiYaniti, not?: string) => void;
  onHata: (hata: Hata | null) => void;
}) {
  const alan = tur === "sonuc" ? "olculebilir_sonuc" : "kendi_rolu";
  const ilk = cikti[alan] ?? "";
  const [metin, setMetin] = useState(ilk);
  const [onay, setOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [formAcik, setFormAcik] = useState(eksik !== null);
  const degisti = metin.trim() !== ilk.trim();

  async function kaydet() {
    setOnay(false);
    setBekleniyor(true);
    onHata(null);
    try {
      const kart = await isKalemiGuncelle(kartId, cikti.id, {
        [alan]: metin.trim() || null,
      });
      onGuncel(
        kart,
        cikti.kanitlar.length > 0 ? YENIDEN_DEGERLENDIRME_NOTU : undefined,
      );
      if (!eksik) setFormAcik(false);
    } catch (sebep) {
      onHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  if (!formAcik) {
    return (
      <div className="flex flex-col gap-2">
        {ilk ? <p className="text-sm text-pretty">{ilk}</p> : null}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-fit"
          onClick={() => setFormAcik(true)}
        >
          Düzenle
        </Button>
      </div>
    );
  }

  const kimlik = `${alan}-${cikti.id}`;
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (!degisti || bekleniyor) return;
        // Değerlendirilmiş çalışmanın göstergesi sıfırlanacak: önce sorulur.
        if (cikti.guven_skoru) setOnay(true);
        else void kaydet();
      }}
    >
      <label htmlFor={kimlik} className="text-sm font-medium">
        {tur === "sonuc"
          ? "Bu çalışma ne sağladı?"
          : "Bu çalışmada sen ne yaptın?"}
      </label>
      <Textarea
        id={kimlik}
        value={metin}
        rows={3}
        onChange={(olay) => setMetin(olay.target.value)}
        placeholder={
          tur === "sonuc"
            ? "ör. Aylık rapor hazırlama süresi 1 günden 10 dakikaya indi."
            : "ör. Backend'i ve veritabanını tek başıma kurdum; arayüzü bir gönüllü yaptı."
        }
      />
      <p className="text-xs text-muted-foreground">
        {tur === "sonuc"
          ? "Sayı verebiliyorsan ver: süre, kullanıcı sayısı, kayıt sayısı gibi."
          : "Ekipçe yaptıysan hangi kısmın sende olduğunu yaz."}
        {referansVar
          ? " Kaydedince önceki referans yanıtı geçmişte kalır."
          : ""}
      </p>
      {onay ? (
        <OnayAlani
          soru={SIFIRLAMA_ONAYI}
          onayEtiketi="Kaydet"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Kaydediliyor…"
          onOnayla={() => void kaydet()}
          onVazgec={() => setOnay(false)}
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="sm" disabled={!degisti || bekleniyor}>
            {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
          </Button>
          {eksik ? null : (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setMetin(ilk);
                setFormAcik(false);
              }}
            >
              Vazgeç
            </Button>
          )}
        </div>
      )}
    </form>
  );
}
