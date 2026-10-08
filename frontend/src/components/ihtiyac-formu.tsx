"use client";

import { useState } from "react";

import { CokluSecim } from "@/components/coklu-secim";
import { useGirisliHesap } from "@/components/giris-kapisi";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { IhtiyacTaslagi, KurumProfili } from "@/lib/api";
import { ISBIRLIGI_TURLERI } from "@/lib/firma-karti";
import { FIRMA_TURLERI, onaydaFirmaBilgisiSorulmali } from "@/lib/firma-profil";
import {
  CALISMA_MODELLERI,
  MUSAITLIK_SECENEKLERI,
  SEHIR_SECENEKLERI,
} from "@/lib/sabitler";

/**
 * İhtiyaç kartı formu: Tanımlama'daki taslak onayı ve panelden ilan düzenleme
 * aynı formu kullanır (docs/kararlar.md D1). `aranan` (kapı) formda
 * yok, değiştirilemez.
 */

export function IhtiyacFormu({
  taslak,
  ortak,
  bekleniyor,
  duzenleme = false,
  baslikGizle = false,
  formId,
  onGonder,
}: {
  taslak: IhtiyacTaslagi;
  ortak: boolean;
  bekleniyor: boolean;
  /** Kayıtlı ilan düzenleniyor: boş filtre bilerek seçilmiş "Fark etmez"dir. */
  duzenleme?: boolean;
  /** Sayfa ya da panel zaten başlık taşıyor: "İhtiyaç kartı taslağınız" yazılmaz. */
  baslikGizle?: boolean;
  /** Verilirse gönder düğmesi formda çizilmez; dışarıdaki düğme `form={formId}` ile gönderir (yan panelin eteği). */
  formId?: string;
  onGonder: (kurumProfili: KurumProfili, taslak: IhtiyacTaslagi) => void;
}) {
  // Firmanın sektörü ve şehri kayıtta alınıyor (docs/kararlar.md
  // F2); onayda yalnızca bu alanlardan önce açılmış hesaplarda sorulur.
  const eksikAlanlar = useGirisliHesap().eksik_profil_alanlari;
  const firmaBilgisiSor =
    !duzenleme && onaydaFirmaBilgisiSorulmali(eksikAlanlar);
  const bosSecim = duzenleme ? FARK_ETMEZ : "";
  const [sektor, setSektor] = useState("");
  const [sehir, setSehir] = useState("");
  // İki ayrı şehir var ve karıştırılıyordu: kurumun bulunduğu yer ile
  // gencin bulunmasını istediğiniz yer. İkincisi eşleştirmenin sert
  // filtresi, o yüzden burada görünür ve düzeltilebilir.
  const [aranilanSehir, setAranilanSehir] = useState(
    taslak.sehir_tercihi ?? "",
  );
  // Tek seçim: iş nerede yapılacak. "Uzaktan" ise şehir filtresi uygulanmaz.
  const [calismaModeli, setCalismaModeli] = useState(
    taslak.calisma_modeli ?? bosSecim,
  );
  // Eşleştirmenin sert filtresi; ajan yanlış anlamış olabilir, kurum düzeltsin.
  const [musaitlik, setMusaitlik] = useState(
    taslak.musaitlik_tercihi ?? bosSecim,
  );
  // Sohbetten çıkan metinler düzenlenebilir (sohbet tavana gelip boş kapatmış olabilir).
  const [problem, setProblem] = useState(taslak.problem_tanimi ?? "");
  const [kriter, setKriter] = useState(taslak.basari_kriteri ?? "");
  const [kisitlar, setKisitlar] = useState(taslak.kisitlar ?? "");
  // Başarı ölçütü: sohbette çıkarılan parçalar düzeltilebilir. Hedef boşsa
  // kart "ölçüm yöntemi belirlenecek" olarak kaydedilir.
  const olcut = taslak.basari_olcutu ?? {};
  const [mevcutDeger, setMevcutDeger] = useState(olcut.mevcut_deger ?? "");
  const [hedefDeger, setHedefDeger] = useState(olcut.hedef_deger ?? "");
  const [sure, setSure] = useState(olcut.sure ?? "");
  // Ortak ilanı (docs/kararlar.md F3): aranan firma türleri ve iş
  // birliği türü; çalışma modeli ve müsaitlik sorulmaz.
  const [firmaTurleri, setFirmaTurleri] = useState<string[]>(
    taslak.aranan_firma_turleri ?? [],
  );
  const [isbirligiTuru, setIsbirligiTuru] = useState(
    taslak.isbirligi_turu ?? "",
  );

  return (
    <form
      id={formId}
      className="@container flex flex-col gap-8"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (bekleniyor) return;
        onGonder(
          {
            sektor: sektor.trim() || null,
            sehir: sehir || null,
          },
          {
            ...taslak,
            problem_tanimi: problem.trim() || null,
            basari_kriteri: kriter.trim() || null,
            basari_olcutu: {
              ...olcut,
              mevcut_deger: mevcutDeger.trim() || null,
              hedef_deger: hedefDeger.trim() || null,
              sure: sure.trim() || null,
            },
            kisitlar: kisitlar.trim() || null,
            sehir_tercihi: aranilanSehir || null,
            calisma_modeli: ortak ? null : secimDegeri(calismaModeli),
            musaitlik_tercihi: ortak ? null : secimDegeri(musaitlik),
            aranan_firma_turleri: ortak ? firmaTurleri : [],
            isbirligi_turu: ortak ? isbirligiTuru || null : null,
          },
        );
      }}
    >
      <section className="flex flex-col gap-4">
        {baslikGizle ? null : (
          <div className="flex flex-col gap-1">
            <h2 className="font-heading text-xl font-semibold text-ana">
              {duzenleme ? "İhtiyaç kartınız" : "İhtiyaç kartı taslağınız"}
            </h2>
            <p className="text-sm text-pretty text-muted-foreground">
              {duzenleme
                ? "Değiştirmek istediğiniz alanları düzeltin, sonra kaydedin."
                : "Sohbetten çıkan kart bu. Gözden geçirin, gerekirse düzeltin, sonra aşağıdan onaylayın."}
            </p>
          </div>
        )}

        <MetinAlani
          id="problem"
          etiket="Problem"
          deger={problem}
          setDeger={setProblem}
          enUzun={PROBLEM_EN_UZUN}
          sohbetteBos={!taslak.problem_tanimi}
        />
        <MetinAlani
          id="basari-kriteri"
          etiket="Başarı kriteri"
          deger={kriter}
          setDeger={setKriter}
          enUzun={KRITER_EN_UZUN}
          sohbetteBos={!taslak.basari_kriteri}
        />
        <div className="flex flex-col gap-3">
          <div className="grid gap-4 @md:grid-cols-3">
            <OlcutAlani
              id="mevcut-deger"
              etiket="Bugünkü durum"
              deger={mevcutDeger}
              setDeger={setMevcutDeger}
            />
            <OlcutAlani
              id="hedef-deger"
              etiket="Hedef"
              deger={hedefDeger}
              setDeger={setHedefDeger}
            />
            <OlcutAlani
              id="sure"
              etiket="Süre"
              deger={sure}
              setDeger={setSure}
            />
          </div>
          {hedefDeger.trim() ? null : (
            <div className="flex flex-col items-start gap-1.5">
              <OlcumBelirlenecekRozeti />
              <p className="text-xs text-pretty text-muted-foreground">
                Hedefi biliyorsanız yukarıya yazın; bilmiyorsanız ihtiyacınız bu
                işaretle kaydedilir.
              </p>
            </div>
          )}
        </div>
        <MetinAlani
          id="kisitlar"
          etiket="Kısıtlar"
          deger={kisitlar}
          setDeger={setKisitlar}
          enUzun={KRITER_EN_UZUN}
          istegeBagli
        />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Firma bilgileri
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            Firma adınız ve iletişim e-postanız kayıtta alındı. E-posta kartta
            görünmez; iletişim iki taraf da onaylayınca açılır.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          <div className="grid gap-4 @md:grid-cols-2">
            {firmaBilgisiSor ? (
              <>
                <FormAlani etiket="Sektör" htmlFor="sektor" istegeBagli>
                  <Input
                    id="sektor"
                    value={sektor}
                    onChange={(olay) => setSektor(olay.target.value)}
                  />
                </FormAlani>

                <FormAlani etiket="Firmanın şehri" htmlFor="sehir" istegeBagli>
                  {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
                      bozuyordu (bkz. backend/app/core/sehir.py). */}
                  <select
                    id="sehir"
                    value={sehir}
                    onChange={(olay) => {
                      setSehir(olay.target.value);
                      // Aranan şehir boşsa kurumun şehri makul bir varsayılan;
                      // kullanıcı yine de değiştirebiliyor.
                      if (!aranilanSehir) setAranilanSehir(olay.target.value);
                    }}
                    className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                  >
                    {SEHIR_SECENEKLERI.map((secenek) => (
                      <option key={secenek.deger} value={secenek.deger}>
                        {secenek.etiket}
                      </option>
                    ))}
                  </select>
                </FormAlani>
              </>
            ) : null}

            <FormAlani
              etiket="Aranan şehir"
              htmlFor="aranilan-sehir"
              istegeBagli
            >
              <select
                id="aranilan-sehir"
                value={aranilanSehir}
                onChange={(olay) => setAranilanSehir(olay.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
              >
                {SEHIR_SECENEKLERI.map((secenek) => (
                  <option key={secenek.deger} value={secenek.deger}>
                    {/* Ortak ilanında şehir varsayılan olarak fark etmez (docs/kararlar.md F5). */}
                    {ortak && secenek.deger === ""
                      ? "Fark etmez"
                      : secenek.etiket}
                  </option>
                ))}
              </select>
            </FormAlani>
          </div>

          {ortak ? (
            <>
              <CokluSecim
                baslik="Aradığınız firma türleri"
                ipucu="(hiçbiri seçilmezse hepsi)"
                secenekler={FIRMA_TURLERI}
                secili={firmaTurleri}
                onDegis={setFirmaTurleri}
              />
              <FormAlani
                etiket="İş birliği türü"
                htmlFor="isbirligi-turu"
                istegeBagli
              >
                <select
                  id="isbirligi-turu"
                  value={isbirligiTuru}
                  onChange={(olay) => setIsbirligiTuru(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="">Belirtmek istemiyorum</option>
                  {ISBIRLIGI_TURLERI.map((tur) => (
                    <option key={tur.deger} value={tur.deger}>
                      {tur.etiket}
                    </option>
                  ))}
                </select>
              </FormAlani>
            </>
          ) : (
            <>
              {/* Eşleştirmenin sert filtreleri: zorunlu seçim. "Fark etmez"
                  boş değer olarak gider ve filtre uygulanmaz; firma bunu
                  unutarak değil, bilerek seçmiş olur. */}
              <FormAlani etiket="Çalışma modeli" htmlFor="calisma-modeli">
                <select
                  id="calisma-modeli"
                  required
                  value={calismaModeli}
                  onChange={(olay) => setCalismaModeli(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="" disabled>
                    Seçin
                  </option>
                  <option value={FARK_ETMEZ}>Fark etmez</option>
                  {CALISMA_MODELLERI.map((model) => (
                    <option key={model.deger} value={model.deger}>
                      {model.etiket}
                    </option>
                  ))}
                </select>
              </FormAlani>

              <FormAlani etiket="Müsaitlik" htmlFor="musaitlik">
                <select
                  id="musaitlik"
                  required
                  value={musaitlik}
                  onChange={(olay) => setMusaitlik(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="" disabled>
                    Seçin
                  </option>
                  <option value={FARK_ETMEZ}>Fark etmez</option>
                  {MUSAITLIK_SECENEKLERI.filter((s) => s.deger).map(
                    (secenek) => (
                      <option key={secenek.deger} value={secenek.deger}>
                        {secenek.etiket}
                      </option>
                    ),
                  )}
                </select>
              </FormAlani>
            </>
          )}

          {ortak ? (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Aranan şehir</span> yalnızca ortağın
              belirli bir şehirde olması şartsa seçilir; seçilmezse şehir fark
              etmez.
            </p>
          ) : firmaBilgisiSor ? (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Firmanın şehri</span> sizin
              bulunduğunuz yer;{" "}
              <span className="font-medium">aranan şehir</span> gencin nerede
              olmasını istediğiniz. Çalışma modeli “Uzaktan” ise aranan şehir
              dikkate alınmaz.
            </p>
          ) : (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Aranan şehir</span>, adayın nerede
              olmasını istediğiniz yer. Çalışma modeli “Uzaktan” ise aranan
              şehir dikkate alınmaz.
            </p>
          )}

          {/* Genç akışı (docs/kararlar.md G1): eşik üstü
              adaylar ihtiyacı fırsat olarak görür. */}
          <p className="text-sm text-pretty text-muted-foreground">
            {duzenleme
              ? "Değişiklikten sonra uygun adaylar yeniden belirlenir; ilgilendiğiniz ve size ilgi gösteren adaylar korunur, onlara ayrıntıların güncellendiği bildirilir."
              : "Onaylanan ihtiyaç, eşleşen adaylara gösterilir."}
          </p>

          {formId ? null : (
            <Button
              type="submit"
              size="lg"
              disabled={bekleniyor}
              className="w-fit"
            >
              {bekleniyor
                ? "Kaydediliyor…"
                : duzenleme
                  ? "Değişiklikleri kaydet"
                  : "Kartı onayla"}
            </Button>
          )}
        </div>
      </section>
    </form>
  );
}

// Zorunlu seçimlerde "Fark etmez": backend'e boş gider (filtre yok).
const FARK_ETMEZ = "fark_etmez";

function secimDegeri(deger: string): string | null {
  return deger && deger !== FARK_ETMEZ ? deger : null;
}

// Backend'deki sınırlarla aynı (app/schemas/tanimlama.py).
const PROBLEM_EN_UZUN = 1000;
const KRITER_EN_UZUN = 500;
const OLCUT_EN_UZUN = 200;

/** Başarı ölçütünün tek satırlık parçası (isteğe bağlı). */
function OlcutAlani({
  id,
  etiket,
  deger,
  setDeger,
}: {
  id: string;
  etiket: string;
  deger: string;
  setDeger: (deger: string) => void;
}) {
  return (
    <FormAlani etiket={etiket} htmlFor={id} istegeBagli>
      <Input
        id={id}
        maxLength={OLCUT_EN_UZUN}
        value={deger}
        onChange={(olay) => setDeger(olay.target.value)}
      />
    </FormAlani>
  );
}

/** Hedef değeri olmayan başarı kriteri. */
export function OlcumBelirlenecekRozeti() {
  return (
    <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
      Ölçüm yöntemi belirlenecek
    </span>
  );
}

/** Taslağın düzenlenebilir metin alanı; sohbette çıkmadıysa bunu söyler. */
function MetinAlani({
  id,
  etiket,
  deger,
  setDeger,
  enUzun,
  sohbetteBos = false,
  istegeBagli = false,
}: {
  id: string;
  etiket: string;
  deger: string;
  setDeger: (deger: string) => void;
  enUzun: number;
  sohbetteBos?: boolean;
  istegeBagli?: boolean;
}) {
  const eksik = !istegeBagli && sohbetteBos && !deger.trim();
  return (
    <FormAlani etiket={etiket} htmlFor={id} istegeBagli={istegeBagli}>
      <Textarea
        id={id}
        rows={3}
        required={!istegeBagli}
        maxLength={enUzun}
        value={deger}
        aria-invalid={eksik || undefined}
        onChange={(olay) => setDeger(olay.target.value)}
        className={eksik ? "border-destructive" : undefined}
      />
      {eksik ? (
        <p className="text-xs text-pretty text-destructive">
          Sohbette netleşmedi. Onaylamadan önce buraya yazın.
        </p>
      ) : null}
    </FormAlani>
  );
}
