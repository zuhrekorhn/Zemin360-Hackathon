import Link from "next/link";

import { BackendDurumu } from "@/components/backend-durumu";
import { BelgeKarti, GuvenGostergesi } from "@/components/kart";
import { Button } from "@/components/ui/button";

const ajanlar = [
  { ad: "Keşif", isi: "Genç yeteneği tanır, yetenek kartına dönüştürür" },
  { ad: "Tanımlama", isi: "Kurumun dağınık ihtiyacını netleştirir" },
  { ad: "Doğrulama", isi: "Somut çıktıları kanıt ve referansla sınar" },
  { ad: "Eşleştirme", isi: "Kart eşleşmesini gerekçesiyle birlikte önerir" },
  { ad: "Canlılık", isi: "Pasifleşen bağlantıları fark eder, hatırlatır" },
  { ad: "Takip", isi: "İş birliğini milestone bazında şeffaf tutar" },
];

// Vitrindeki örnek: gerçek ekranlarla AYNI bileşenler, ama sabit veriyle.
// Ana sayfa backend kapalıyken de eksiksiz görünmeli — burası ürünün ne
// yaptığını anlatan yer, canlı veriye bağlamanın bir faydası yok.
const ORNEK_GUVEN_SKORU = {
  kanit_orijinalligi: 3,
  sonuc_olculebilirligi: 2,
  rol_netligi: 3,
  ucuncu_taraf_onayi: 2,
  gerekce_metni: null,
};

const ORNEK_GEREKCE = [
  "Aynı problemi çözen, çalışan bir sistem kurmuş.",
  "Sonucu sayıyla anlatmış: 400 kitap, 120 üye.",
  "Kanıt linki açıldı, kütüphane sorumlusu referansı yanıtladı.",
];

export default function AnaSayfa() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-16 px-6 py-16 sm:py-24">
      <header className="flex flex-col items-center gap-5 text-center">
        <h1 className="font-heading text-3xl leading-[1.15] font-semibold text-balance text-ana sm:text-[2.75rem]">
          Bir kişinin ne yaptığını, gerçekten yaptığını gösterebilmek.
        </h1>

        <p className="max-w-xl text-base text-pretty text-muted-foreground">
          Genç yetenekler ve kurumlar aynı veri katmanında buluşuyor. Sohbetle
          başlıyor, kanıtla doğrulanıyor, gerekçesi açık bir eşleşmeyle
          sonuçlanıyor.
        </p>
      </header>

      {/* Sohbet paneli — yuvarlak ve sıcak (docs/design-language.md § Yerleşim) */}
      <section aria-labelledby="ornek-akis" className="flex flex-col gap-6">
        <h2 id="ornek-akis" className="sr-only">
          Örnek akış
        </h2>

        <div className="flex flex-col gap-3 rounded-[1.75rem] bg-muted p-5 sm:p-6">
          <p className="max-w-[85%] rounded-3xl rounded-bl-lg bg-card px-4 py-3 text-sm text-pretty ring-1 ring-kenar">
            <span className="mb-1 block font-medium text-baglanti">
              Keşif Ajanı
            </span>
            Son bir yılda bitirdiğin, sonucunu görebildiğin bir iş var mı?
            Okuldan ya da gönüllü bir işten de olabilir.
          </p>

          <p className="ml-auto max-w-[85%] rounded-3xl rounded-br-lg bg-ana px-4 py-3 text-sm text-pretty text-zemin">
            Mahalle kütüphanesine ödünç takip sistemi yazdım. 400 kitabı ve 120
            üyeyi takip ediyor.
          </p>
        </div>

        {/* Gerekçe kartı — öneri ekranındaki bileşenin ta kendisi
            (docs/design-language.md: hairline çizgi, resmi belge hissi).
            Sayfadaki tek bilinçli hareket burada. */}
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-700">
          <BelgeKarti
            baslik="Neden eşleşti"
            altbaslik="Üye kayıtlarını elle tutmaktan kurtulmak isteyen bir kooperatifin ihtiyacıyla"
            etek={<GuvenGostergesi skor={ORNEK_GUVEN_SKORU} />}
          >
            <ul className="flex flex-col gap-2.5">
              {ORNEK_GEREKCE.map((satir) => (
                <li key={satir}>{satir}</li>
              ))}
            </ul>
          </BelgeKarti>
        </div>
      </section>

      {/* İki giriş yolu — kart kalıbı yerine hairline ile ayrılmış iki sütun */}
      <section className="grid gap-8 border-t border-kenar pt-10 sm:grid-cols-2 sm:gap-10 sm:divide-x sm:divide-kenar">
        <div className="flex flex-col items-start gap-3 sm:pr-10">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Genç yetenek
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            Keşif Ajanı’yla kısa bir sohbet. Ne yaptığını ve neyi somut olarak
            ortaya çıkardığını birlikte bir yetenek kartına dönüştürürsünüz. CV
            yüklemek yok.
          </p>
          <Button asChild size="lg" className="mt-2">
            <Link href="/kesif">Genç olarak başla</Link>
          </Button>
        </div>

        <div className="flex flex-col items-start gap-3 border-t border-kenar pt-8 sm:border-t-0 sm:pt-0 sm:pl-10">
          <h2 className="font-heading text-xl font-semibold text-ana">Kurum</h2>
          <p className="text-sm text-pretty text-muted-foreground">
            Tanımlama Ajanı’yla kısa bir sohbet. “Dijitalleşmek istiyoruz” gibi
            bir cümleyi, ölçülebilir başarı kriteri olan net bir ihtiyaç kartına
            çevirirsiniz.
          </p>
          <Button asChild size="lg" variant="outline" className="mt-2">
            <Link href="/tanimlama">Kurum olarak başla</Link>
          </Button>
        </div>
      </section>

      <section className="flex flex-col gap-4 border-t border-kenar pt-10">
        <h2 className="font-heading text-xl font-semibold text-ana">
          Altı problem, altı ajan
        </h2>
        <ul className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
          {ajanlar.map((ajan) => (
            <li key={ajan.ad} className="flex flex-col gap-0.5">
              <span className="text-sm font-medium">{ajan.ad} Ajanı</span>
              <span className="text-sm text-muted-foreground">{ajan.isi}</span>
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-auto flex flex-col gap-3 border-t border-kenar pt-8">
        <BackendDurumu />
        <p className="text-xs text-muted-foreground">
          Zemin360 Hackathon · GİRVAK — Faz 2. Yukarıdaki örnek sabit; Keşif,
          Tanımlama, Eşleştirme ve Doğrulama ekranları gerçek veriyle çalışıyor.
        </p>
      </footer>
    </main>
  );
}
