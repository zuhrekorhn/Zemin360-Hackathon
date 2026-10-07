"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { OnayAlani } from "@/components/onay-alani";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { FormDugmeleri } from "@/components/ui/form-dugmeleri";
import { Input } from "@/components/ui/input";
import { type KanitParcasi, kanitDosyasiAdresi } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  KABUL_EDILEN_DOSYALAR,
  type SecenekKutusu as SecenekKutusuVerisi,
  dosyaBoyutu,
  girvakIncelemesiMetni,
  kanitAdresi,
  okunamayanSecenekleri,
} from "@/lib/kanit";

/**
 * Kanıt parçaları (docs/dogrulama.md § 3): link ve dosya satırları, ekleme
 * formları. "Güçlendir" paneli (guclendir-paneli.tsx) bunları adım adım dizer.
 * Okunamayan linkin altında seçenek kutusu; dosyayı varsayılan olarak yalnızca
 * genç ve GİRVAK görür, genç firmalara açabilir.
 */

export function KanitSatiri({
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
export async function indir(
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

export function DosyaSatiri({
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

export function DosyaEkleFormu({
  kimlik,
  bekleniyor,
  onEkle,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onEkle: (dosya: File) => Promise<boolean>;
  onVazgec?: () => void;
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

export function LinkEkleFormu({
  kimlik,
  bekleniyor,
  onEkle,
  onVazgec,
}: {
  kimlik: string;
  bekleniyor: boolean;
  onEkle: (url: string) => Promise<boolean>;
  onVazgec?: () => void;
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
