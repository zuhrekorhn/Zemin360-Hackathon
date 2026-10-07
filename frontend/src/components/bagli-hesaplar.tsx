"use client";

/**
 * Profildeki "Bağlı hesaplar" bölümü (docs/dogrulama.md § 6).
 *
 * İki yol: giriş yaparak bağlama (GitHub, GitLab, ORCID; ayarı olmayan
 * görünmez) ve doğrulama kodu (kod profil açıklamasına yazılır, sonra kontrol
 * edilir). Profil okunamazsa GİRVAK elle doğrular; sonuç bildirim olarak gelir.
 * Kaldırma sayfa içinde onaylanır.
 */

import { useEffect, useRef, useState } from "react";

import { OnayAlani } from "@/components/onay-alani";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SECIM_SINIFI } from "@/components/ui/secim";
import { KUTU } from "@/components/ui/yuzey";
import {
  type BagliHesap,
  type Hesaplarim,
  type ProfilKodu,
  baglantiyiKaldir,
  hesaplarim,
  oauthBaslat,
  profilKoduAl,
  profilKodunuDogrula,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  kalanSure,
  kodYonergesi,
  platformAdi,
  profilOrnegi,
  yontemEtiketi,
} from "@/lib/hesap-baglama";
import { cn } from "@/lib/utils";

export function BagliHesaplar() {
  const [veri, setVeri] = useState<Hesaplarim | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const [kodFormuAcik, setKodFormuAcik] = useState(false);
  const okundu = useRef(false);
  // Zaten bağlı sağlayıcıya ikinci kez "bağla" düğmesi gösterilmez.
  const baglanabilir = (veri?.oauth_saglayicilari ?? []).filter(
    (saglayici) => !veri?.hesaplar.some((h) => h.saglayici === saglayici),
  );

  function yenile() {
    hesaplarim()
      .then(setVeri)
      .catch((sebep) => setHata(hatayaCevir(sebep)));
  }

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    yenile();
  }, []);

  return (
    <section
      id="hesaplar"
      aria-labelledby="hesaplar-baslik"
      className={cn(KUTU, "flex scroll-mt-24 flex-col gap-5 px-6 py-6")}
    >
      <div className="flex flex-col gap-1">
        <h2
          id="hesaplar-baslik"
          className="font-heading text-lg font-semibold text-ana"
        >
          Bağlı hesaplar
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Çalışmaların GitHub, YouTube, Medium gibi bir hesapta duruyorsa
          hesabını bağla. Böylece çalışmanın sana ait olduğu görülür ve güven
          göstergen güçlenir.
        </p>
      </div>

      {hata ? <HataKutusu hata={hata} /> : null}
      {veri ? (
        <>
          <HesapListesi hesaplar={veri.hesaplar} onDegisti={setVeri} />
          {veri.inceleme_bekleyen ? (
            <p
              className="text-sm text-pretty text-muted-foreground"
              role="status"
            >
              {platformAdi(veri.inceleme_bekleyen)} sayfanı otomatik okuyamadık;
              GİRVAK kodu kendisi kontrol edecek. Sonucu bildirim olarak
              göreceksin.
            </p>
          ) : null}
          {baglanabilir.length > 0 ? (
            <OauthDugmeleri saglayicilar={baglanabilir} />
          ) : null}
          {veri.bekleyen_kodlar.map((kod) => (
            <KodKutusu key={kod.platform} kod={kod} onDegisti={yenile} />
          ))}
          {veri.profil_kodu_platformlari.length > 0 ? (
            kodFormuAcik ? (
              <div className="rounded-md border border-kenar bg-zemin px-4 py-4">
                <KodAlmaFormu
                  platformlar={veri.profil_kodu_platformlari}
                  onAlindi={() => {
                    setKodFormuAcik(false);
                    yenile();
                  }}
                  onVazgec={() => setKodFormuAcik(false)}
                />
              </div>
            ) : (
              <Button
                type="button"
                variant="ghost"
                className="w-fit px-0 text-baglanti underline underline-offset-4 hover:bg-transparent"
                onClick={() => setKodFormuAcik(true)}
              >
                YouTube, Medium, Behance gibi başka bir hesabı bağla
              </Button>
            )
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function HesapListesi({
  hesaplar,
  onDegisti,
}: {
  hesaplar: BagliHesap[];
  onDegisti: (yeni: Hesaplarim) => void;
}) {
  if (hesaplar.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Henüz bağlı hesabın yok.</p>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
      {hesaplar.map((hesap) => (
        <HesapSatiri key={hesap.id} hesap={hesap} onDegisti={onDegisti} />
      ))}
    </ul>
  );
}

function HesapSatiri({
  hesap,
  onDegisti,
}: {
  hesap: BagliHesap;
  onDegisti: (yeni: Hesaplarim) => void;
}) {
  const [onay, setOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);

  async function kaldir() {
    setBekleniyor(true);
    setHata(null);
    try {
      onDegisti(await baglantiyiKaldir(hesap.id));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleniyor(false);
      setOnay(false);
    }
  }

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-sm font-medium">
            {platformAdi(hesap.saglayici)} · {hesap.kullanici_adi}
          </span>
          <span className="text-xs text-muted-foreground">
            {yontemEtiketi(hesap.yontem)}
          </span>
        </div>
        {onay ? null : (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setOnay(true)}
          >
            Kaldır
          </Button>
        )}
      </div>
      {onay ? (
        <OnayAlani
          soru={`${platformAdi(hesap.saglayici)} hesabının bağlantısı kaldırılsın mı? Bu hesaptaki çalışmaların yeniden değerlendirilir.`}
          onayEtiketi="Bağlantıyı kaldır"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Kaldırılıyor…"
          onOnayla={() => void kaldir()}
          onVazgec={() => setOnay(false)}
        />
      ) : null}
      {hata ? <HataKutusu hata={hata} /> : null}
    </li>
  );
}

function OauthDugmeleri({ saglayicilar }: { saglayicilar: string[] }) {
  const [bekleyen, setBekleyen] = useState<string | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);

  async function baslat(saglayici: string) {
    setBekleyen(saglayici);
    setHata(null);
    try {
      const { yetki_adresi } = await oauthBaslat(saglayici);
      // Sağlayıcı onaydan sonra /hesap-baglama/{saglayici} sayfasına döner.
      window.location.assign(yetki_adresi);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleyen(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {saglayicilar.map((saglayici) => (
          <Button
            key={saglayici}
            type="button"
            variant="outline"
            disabled={bekleyen !== null}
            onClick={() => void baslat(saglayici)}
          >
            {bekleyen === saglayici
              ? "Yönlendiriliyor…"
              : `${platformAdi(saglayici)} hesabını bağla`}
          </Button>
        ))}
      </div>
      {hata ? <HataKutusu hata={hata} /> : null}
    </div>
  );
}

function KodKutusu({
  kod,
  onDegisti,
}: {
  kod: ProfilKodu;
  onDegisti: () => void;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const kalan = kalanSure(kod.son_gecerlilik, new Date());

  async function kontrolEt() {
    setBekleniyor(true);
    setHata(null);
    try {
      await profilKodunuDogrula(kod.platform);
      onDegisti();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-sm border border-kenar p-4">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-medium">
          {platformAdi(kod.platform)} doğrulama kodun
        </span>
        <code className="w-fit rounded-sm bg-muted px-2 py-1 font-mono text-base select-all">
          {kod.kod}
        </code>
      </div>
      <p className="text-sm text-pretty text-muted-foreground">
        {kodYonergesi(kod.platform, kod.kod)}{" "}
        <a
          href={kod.profil_adresi}
          target="_blank"
          rel="noreferrer"
          className="text-baglanti underline"
        >
          {platformAdi(kod.platform)} sayfanı aç
        </a>
        {kalan ? ` · ${kalan}` : null}
      </p>
      {hata ? <HataKutusu hata={hata} /> : null}
      <Button
        type="button"
        size="sm"
        className="w-fit"
        disabled={bekleniyor}
        onClick={() => void kontrolEt()}
      >
        {bekleniyor ? "Kontrol ediliyor…" : "Kodu kontrol et"}
      </Button>
    </div>
  );
}

function KodAlmaFormu({
  platformlar,
  onAlindi,
  onVazgec,
}: {
  platformlar: string[];
  onAlindi: () => void;
  onVazgec: () => void;
}) {
  const [platform, setPlatform] = useState(platformlar[0] ?? "");
  const [adres, setAdres] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);

  async function kodAl(olay: React.FormEvent) {
    olay.preventDefault();
    if (!platform || !adres.trim() || bekleniyor) return;
    setBekleniyor(true);
    setHata(null);
    try {
      await profilKoduAl(platform, adres.trim());
      setAdres("");
      onAlindi();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  if (platformlar.length === 0) return null;
  return (
    <form className="flex flex-col gap-3" onSubmit={kodAl}>
      <p className="text-sm text-pretty">
        Doğrulama kodu al: kodu o hesabın açıklamasına ekle, biz de orada
        görelim.
      </p>
      <div className="grid gap-3 sm:grid-cols-[12rem_1fr]">
        <FormAlani etiket="Hesap türü" htmlFor="kod-platform">
          <select
            id="kod-platform"
            value={platform}
            onChange={(olay) => setPlatform(olay.target.value)}
            className={SECIM_SINIFI}
          >
            {platformlar.map((p) => (
              <option key={p} value={p}>
                {platformAdi(p)}
              </option>
            ))}
          </select>
        </FormAlani>
        <FormAlani etiket="Hesabının adresi" htmlFor="kod-adres">
          <Input
            id="kod-adres"
            value={adres}
            maxLength={500}
            placeholder={profilOrnegi(platform)}
            onChange={(olay) => setAdres(olay.target.value)}
          />
        </FormAlani>
      </div>
      {hata ? <HataKutusu hata={hata} /> : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={!adres.trim() || bekleniyor}>
          {bekleniyor ? "Kod hazırlanıyor…" : "Kod al"}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onVazgec}>
          Vazgeç
        </Button>
      </div>
    </form>
  );
}
