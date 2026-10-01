"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type FormCevabi,
  type ReferansIliskisi,
  type ReferansIstegiBilgisi,
  type ReferansYanitiSonucu,
  referansIstegiGetir,
  referansYanitla,
} from "@/lib/api";
import { type Hata, hatayaCevir, tekrarDenenebilirMi } from "@/lib/hata";
import {
  CEVAP_SECENEKLERI,
  type FormSorusu,
  ILISKI_SECENEKLERI,
  formSorulari,
} from "@/lib/referans";

/**
 * Referans kişinin yanıt sayfası (docs/sequence-diagrams.md § Akış 2).
 *
 * Giriş yok, kimlik yerine tek kullanımlık token — referans kişiyi üye olmaya
 * zorlamak yanıt oranını düşürür (docs/api-contracts.md § Mimari Notlar).
 *
 * İddia formdan ÖNCE gösteriliyor: neyi onayladığını bilmeden yanıt vermek
 * anlamsız olurdu. Harcanmış ya da geçersiz bir link form açmıyor.
 *
 * Dört soru (docs/plans/dogrulama-iyilestirme.md § 7): ilişki; çalışma, pay ve
 * sonuç doğru mu. Pay ve sonuç ayrı satırlarda gösterilir; kalemde yazılmamışsa
 * o soru sorulmaz.
 */

type Yanitlar = Partial<Record<FormSorusu["alan"], FormCevabi>>;

const KAPALI_MESAJLARI: Record<string, string> = {
  yanitlandi:
    "Bu referans isteği zaten yanıtlanmış. Link tek kullanımlık; yeniden yanıt vermeniz gerekmiyor.",
  yanit_yok:
    "Bu referans isteğinin süresi doldu (7 gün). Yanıt gelmemesi kimse için olumsuz bir işaret değil; çalışma referans yanıtı olmadan değerlendirildi.",
  geri_cekildi: "Bu referans isteği geri çekildi. Yanıt vermeniz gerekmiyor.",
};

export default function ReferansSayfasi() {
  return (
    <Suspense fallback={null}>
      <ReferansFormu />
    </Suspense>
  );
}

function ReferansFormu() {
  const token = useSearchParams().get("token");

  const [bilgi, setBilgi] = useState<ReferansIstegiBilgisi | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [iliski, setIliski] = useState<ReferansIliskisi | null>(null);
  const [yanitlar, setYanitlar] = useState<Yanitlar>({});
  const [yorum, setYorum] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  // Kalıcı hatalarda (404/409) "Tekrar dene" göstermiyoruz.
  const [tekrarDenenir, setTekrarDenenir] = useState(true);
  const [sonuc, setSonuc] = useState<ReferansYanitiSonucu | null>(null);
  const okundu = useRef(false);

  const bilgiyiGetir = useCallback(async (kimlik: string) => {
    setHata(null);
    setYukleniyor(true);
    try {
      setBilgi(await referansIstegiGetir(kimlik));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setTekrarDenenir(tekrarDenenebilirMi(sebep));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;

    async function baslat() {
      if (token) await bilgiyiGetir(token);
      else setYukleniyor(false);
    }

    void baslat();
  }, [token, bilgiyiGetir]);

  const sorular = bilgi ? formSorulari(bilgi) : [];
  const tamam = iliski !== null && sorular.every((soru) => yanitlar[soru.alan]);

  async function gonder() {
    if (!token || !tamam || iliski === null || !yanitlar.iddia_dogru) return;
    setHata(null);
    setBekleniyor(true);
    try {
      setSonuc(
        await referansYanitla(token, {
          iliski,
          iddia_dogru: yanitlar.iddia_dogru,
          pay_dogru: yanitlar.pay_dogru ?? null,
          sonuc_dogru: yanitlar.sonuc_dogru ?? null,
          yorum: yorum.trim() || null,
        }),
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setTekrarDenenir(tekrarDenenebilirMi(sebep));
      // 409: bu arada başka bir sekmede yanıtlanmış olabilir — durumu tazele.
      if (!tekrarDenenebilirMi(sebep)) void bilgiyiGetir(token);
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Bir referans isteği"
        aciklama="Biri, birlikte yürüttüğünüz bir çalışmayı Zemin360’ta kendi yetenek kartına ekledi ve sizi referans gösterdi. Üye olmanız gerekmiyor; dört kısa soru."
      />

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={
            tekrarDenenir && token ? () => void bilgiyiGetir(token) : undefined
          }
        />
      ) : null}

      {yukleniyor ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          İstek yükleniyor…
        </p>
      ) : null}

      {!yukleniyor && !token ? (
        <Bilgilendirme metin="Bu adreste referans kodu yok. Size iletilen linki olduğu gibi açın." />
      ) : null}

      {bilgi ? <Iddia bilgi={bilgi} /> : null}

      {sonuc ? <Tesekkur sonuc={sonuc} /> : null}

      {bilgi && !sonuc && !bilgi.yanitlanabilir ? (
        <Bilgilendirme
          metin={
            KAPALI_MESAJLARI[bilgi.durum] ??
            "Bu referans isteği artık yanıtlanamıyor."
          }
        />
      ) : null}

      {bilgi && !sonuc && bilgi.yanitlanabilir ? (
        <form
          className="flex flex-col gap-6"
          onSubmit={(olay) => {
            olay.preventDefault();
            void gonder();
          }}
        >
          <p className="text-sm text-pretty text-muted-foreground">
            Yanıtlarınız güven göstergesinin yalnızca “Referans” kısmını besler;
            pay ve sonuç için “evet” demeniz o başlıklara destek sayılır.
            Olumsuz yanıt da işimize yarar; amacımız kimseyi cezalandırmak
            değil, çalışmayı doğru yere oturtmak. Emin olmadığınız soruda
            “Bilmiyorum” deyin.
          </p>

          <SecenekGrubu
            ad="iliski"
            soru="Bu kişiyi nereden tanıyorsunuz?"
            secenekler={ILISKI_SECENEKLERI}
            secili={iliski}
            onSec={setIliski}
          />

          {sorular.map((soru) => (
            <SecenekGrubu
              key={soru.alan}
              ad={soru.alan}
              soru={soru.soru}
              ayrinti={soru.ayrinti}
              secenekler={CEVAP_SECENEKLERI}
              secili={yanitlar[soru.alan] ?? null}
              onSec={(cevap) =>
                setYanitlar((once) => ({ ...once, [soru.alan]: cevap }))
              }
              yatay
            />
          ))}

          <FormAlani
            etiket="Eklemek istediğiniz bir şey"
            htmlFor="yorum"
            istegeBagli
          >
            <textarea
              id="yorum"
              value={yorum}
              onChange={(olay) => setYorum(olay.target.value)}
              rows={3}
              placeholder="ör. sistemi kendisi kurdu, hâlâ kullanıyoruz."
              className="w-full resize-y rounded-2xl border border-kenar bg-card px-4 py-3 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
            />
          </FormAlani>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" size="lg" disabled={bekleniyor || !tamam}>
              {bekleniyor ? "Gönderiliyor…" : "Yanıtı gönder"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Bu link tek kullanımlık.
            </span>
          </div>
        </form>
      ) : null}
    </Sayfa>
  );
}

/** Tek seçimli soru; seçenekler etiketli radyo düğmeleri. */
function SecenekGrubu<T extends string>({
  ad,
  soru,
  ayrinti,
  secenekler,
  secili,
  onSec,
  yatay = false,
}: {
  ad: string;
  soru: string;
  ayrinti?: string | null;
  secenekler: { deger: T; etiket: string }[];
  secili: T | null;
  onSec: (deger: T) => void;
  yatay?: boolean;
}) {
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="font-heading text-base font-semibold text-ana">
        {soru}
      </legend>
      {ayrinti ? (
        <p className="rounded-sm border-l-2 border-kenar pl-3 text-sm text-pretty">
          {ayrinti}
        </p>
      ) : null}
      <div className={yatay ? "flex flex-wrap gap-2" : "flex flex-col gap-2"}>
        {secenekler.map((secenek) => (
          <label
            key={secenek.deger}
            className={
              secili === secenek.deger
                ? "flex cursor-pointer items-center gap-3 rounded-sm border border-baglanti bg-muted px-4 py-3 text-sm"
                : "flex cursor-pointer items-center gap-3 rounded-sm border border-kenar bg-card px-4 py-3 text-sm"
            }
          >
            <input
              type="radio"
              name={ad}
              value={secenek.deger}
              checked={secili === secenek.deger}
              onChange={() => onSec(secenek.deger)}
              className="accent-baglanti"
            />
            {secenek.etiket}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** Referans kişinin yanıt verirken baktığı iddia. */
function Iddia({ bilgi }: { bilgi: ReferansIstegiBilgisi }) {
  return (
    <article className="rounded-sm border border-kenar bg-card">
      <div className="border-b border-kenar px-5 py-4">
        <p className="text-xs text-muted-foreground">Çalışmanın sahibi</p>
        <p className="text-sm">{bilgi.iddia_sahibi_adi}</p>
      </div>
      <div className="flex flex-col gap-1 px-5 py-4">
        <h2 className="font-heading text-base font-semibold text-ana">
          {bilgi.baslik}
        </h2>
        {bilgi.aciklama ? (
          <p className="text-sm text-pretty">{bilgi.aciklama}</p>
        ) : null}
      </div>
    </article>
  );
}

function Bilgilendirme({ metin }: { metin: string }) {
  return (
    <p className="rounded-sm border border-kenar bg-card px-5 py-4 text-sm text-pretty">
      {metin}
    </p>
  );
}

function Tesekkur({ sonuc }: { sonuc: ReferansYanitiSonucu }) {
  return (
    <section className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-5 py-4">
      <h2 className="font-heading text-xl font-semibold text-ana">
        Teşekkürler, yanıtınız kaydedildi
      </h2>
      <p className="text-sm text-pretty">
        “{sonuc.baslik}” için verdiğiniz yanıt işlendi. Bu linki tekrar açmanıza
        gerek yok.
      </p>
      <p className="text-sm text-pretty text-muted-foreground">
        Yanıtınız tek başına bir karar değil: güven göstergesinin “Referans”
        kısmını besliyor; pay ve sonuç için “evet” dediyseniz o başlıklara da
        destek oluyor.
      </p>
    </section>
  );
}
