"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { type KanitDurumu, referansYanitla } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * Referans kişinin yanıt sayfası (docs/sequence-diagrams.md § Akış 2).
 *
 * Giriş yok, kimlik yerine tek kullanımlık token — referans kişiyi üye olmaya
 * zorlamak yanıt oranını düşürür (docs/api-contracts.md § Mimari Notlar).
 *
 * Bu sayfa iddia sahibinin kartını göstermiyor: referans kişi neyi
 * onayladığını çıktının başlığından görüyor, puanını da kartın geri kalanından
 * etkilenmeden veriyor.
 */

const SECENEKLER = [
  { puan: 1, etiket: "1 — Bu iş böyle olmadı" },
  { puan: 2, etiket: "2 — Katkısı sınırlıydı" },
  { puan: 3, etiket: "3 — Ne iyi ne kötü" },
  { puan: 4, etiket: "4 — Anlatıldığı gibi yaptı" },
  { puan: 5, etiket: "5 — Anlatılandan da fazlasını yaptı" },
];

export default function ReferansSayfasi() {
  return (
    <Suspense fallback={null}>
      <ReferansFormu />
    </Suspense>
  );
}

function ReferansFormu() {
  const token = useSearchParams().get("token");

  const [puan, setPuan] = useState<number | null>(null);
  const [yorum, setYorum] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const [sonuc, setSonuc] = useState<KanitDurumu | null>(null);

  async function gonder() {
    if (!token || puan === null) return;
    setHata(null);
    setBekleniyor(true);
    try {
      setSonuc(await referansYanitla(token, puan, yorum.trim() || null));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Bir referans isteği
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Biri, birlikte çalıştığınız bir işi Zemin360’ta kendi yetenek kartına
          ekledi ve sizi referans gösterdi. Üye olmanız gerekmiyor; tek bir
          soruluk bir şey.
        </p>
      </header>

      {hata ? (
        <HataKutusu hata={hata} tekrarDene={() => void gonder()} />
      ) : null}

      {!token ? (
        <p className="rounded-sm border border-kenar bg-card px-5 py-4 text-sm text-pretty">
          Bu adreste referans kodu yok. Size iletilen linki olduğu gibi açın.
        </p>
      ) : sonuc ? (
        <Tesekkur sonuc={sonuc} />
      ) : (
        <form
          className="flex flex-col gap-6"
          onSubmit={(olay) => {
            olay.preventDefault();
            void gonder();
          }}
        >
          <fieldset className="flex flex-col gap-3">
            <legend className="font-heading text-base font-semibold text-ana">
              Anlatılan iş, sizin gördüğünüz kadarıyla doğru mu?
            </legend>
            <p className="text-sm text-muted-foreground">
              Yanıtınız bir puana değil, dört başlıktan yalnızca birine etki
              eder. Olumsuz yanıt da işimize yarar — amacımız kimseyi
              cezalandırmak değil, iddiayı yerine oturtmak.
            </p>

            {SECENEKLER.map((secenek) => (
              <label
                key={secenek.puan}
                className={
                  puan === secenek.puan
                    ? "flex cursor-pointer items-center gap-3 rounded-sm border border-baglanti bg-muted px-4 py-3 text-sm"
                    : "flex cursor-pointer items-center gap-3 rounded-sm border border-kenar bg-card px-4 py-3 text-sm"
                }
              >
                <input
                  type="radio"
                  name="puan"
                  value={secenek.puan}
                  checked={puan === secenek.puan}
                  onChange={() => setPuan(secenek.puan)}
                  className="accent-baglanti"
                />
                {secenek.etiket}
              </label>
            ))}
          </fieldset>

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
              placeholder="Örn. sistemi kendisi kurdu, hâlâ kullanıyoruz."
              className="w-full resize-y rounded-2xl border border-kenar bg-card px-4 py-3 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
            />
          </FormAlani>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              size="lg"
              disabled={bekleniyor || puan === null}
            >
              {bekleniyor ? "Gönderiliyor…" : "Yanıtı gönder"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Bu link tek kullanımlık.
            </span>
          </div>
        </form>
      )}
    </main>
  );
}

function Tesekkur({ sonuc }: { sonuc: KanitDurumu }) {
  return (
    <section className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-5 py-4">
      <h2 className="font-heading text-xl font-semibold text-ana">
        Teşekkürler, yanıtınız kaydedildi
      </h2>
      <p className="text-sm text-pretty">
        “{sonuc.baslik}” iddiası için verdiğiniz yanıt işlendi. Bu linki tekrar
        açmanıza gerek yok.
      </p>
      <p className="text-sm text-pretty text-muted-foreground">
        Yanıtınız tek başına bir karar değil: dört başlıklı güven göstergesinin
        yalnızca “üçüncü taraf onayı” kısmını besliyor, diğer üçü kanıtın
        kendisinden geliyor.
      </p>
    </section>
  );
}
