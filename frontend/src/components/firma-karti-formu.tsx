"use client";

import { CokluSecim } from "@/components/coklu-secim";
import { FormAlani } from "@/components/sohbet";
import { Input } from "@/components/ui/input";
import {
  type FirmaKartiFormu,
  ISBIRLIGI_TURLERI,
  YETKINLIK_EN_COK,
} from "@/lib/firma-karti";

const METIN_KUTUSU =
  "w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30";

/**
 * Firma kartının alanları (docs/kararlar.md F3). Sohbetten gelen
 * taslağın onayı ve kartın düzenlenmesi aynı parçayı kullanır; doğrulama
 * `lib/firma-karti.ts`'de. Firmaya "siz".
 */
export function FirmaKartiFormAlanlari({
  form,
  onDegis,
}: {
  form: FirmaKartiFormu;
  onDegis: (form: FirmaKartiFormu) => void;
}) {
  function alan<K extends keyof FirmaKartiFormu>(
    ad: K,
    deger: FirmaKartiFormu[K],
  ) {
    onDegis({ ...form, [ad]: deger });
  }

  return (
    <div className="flex flex-col gap-5">
      <FormAlani etiket="Ne yapıyorsunuz?" htmlFor="kart-ne">
        <textarea
          id="kart-ne"
          value={form.ne_yapiyoruz}
          rows={3}
          required
          onChange={(olay) => alan("ne_yapiyoruz", olay.target.value)}
          className={METIN_KUTUSU}
        />
      </FormAlani>

      <FormAlani etiket="Yetkinlikler" htmlFor="kart-yetkinlik">
        <Input
          id="kart-yetkinlik"
          value={form.yetkinlikler}
          required
          onChange={(olay) => alan("yetkinlikler", olay.target.value)}
        />
      </FormAlani>
      <p className="-mt-3 text-xs text-pretty text-muted-foreground">
        Virgülle ayırın; en çok {YETKINLIK_EN_COK} tane.
      </p>

      <FormAlani etiket="Önceki işleriniz" htmlFor="kart-onceki" istegeBagli>
        <textarea
          id="kart-onceki"
          value={form.onceki_isler}
          rows={3}
          onChange={(olay) => alan("onceki_isler", olay.target.value)}
          className={METIN_KUTUSU}
        />
      </FormAlani>

      <FormAlani
        etiket="Nasıl bir ortak arıyorsunuz?"
        htmlFor="kart-aranan"
        istegeBagli
      >
        <textarea
          id="kart-aranan"
          value={form.aranan_isbirligi}
          rows={2}
          onChange={(olay) => alan("aranan_isbirligi", olay.target.value)}
          className={METIN_KUTUSU}
        />
      </FormAlani>

      <CokluSecim
        baslik="İş birliği türleri"
        ipucu="(isteğe bağlı)"
        secenekler={ISBIRLIGI_TURLERI}
        secili={form.isbirligi_turleri}
        onDegis={(secili) => alan("isbirligi_turleri", secili)}
      />
    </div>
  );
}
