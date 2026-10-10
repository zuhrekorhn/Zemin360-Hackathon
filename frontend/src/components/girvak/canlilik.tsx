import Link from "next/link";

import { YanKutu } from "@/components/genc-paneli";
import {
  BosDurum,
  DurumEtiketi,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import type { CanlilikOlayi, PasifBaglanti, TaramaSonucu } from "@/lib/api";
import {
  TAKILMA_SURELERI,
  alicilarMetni,
  pasifSureMetni,
  turEtiketi,
} from "@/lib/canlilik";
import { cn } from "@/lib/utils";

const LISTE = "flex flex-col gap-3";
const SATIR = cn(KUTU, "flex flex-col gap-1 px-5 py-4");

/** Yan sütun: "Şimdi kontrol et" ve son kontrolün özeti. */
export function KontrolKutusu({
  taraniyor,
  sonuc,
  onCalistir,
}: {
  taraniyor: boolean;
  sonuc: TaramaSonucu | null;
  onCalistir: () => void;
}) {
  return (
    <YanKutu baslik="Takılanları kontrol et">
      <p className="text-sm text-pretty text-muted-foreground">
        Cevapsız kalan öneri ve ilgiler, onaylanmayan planlar ve gecikmiş
        adımlar için ilgili kişiye hatırlatma gönderir. Aynı kişiye aynı konuda
        ikinci kez hatırlatma gitmez.
      </p>
      <Button
        type="button"
        size="lg"
        disabled={taraniyor}
        onClick={onCalistir}
        className="w-full"
      >
        {taraniyor ? "Kontrol ediliyor…" : "Şimdi kontrol et"}
      </Button>
      {sonuc ? <TaramaOzeti sonuc={sonuc} /> : null}
    </YanKutu>
  );
}

/** Yan sütun: hangi durumun kaç gün sonra takılmış sayıldığı. */
export function TakilmaSureleri() {
  return (
    <YanKutu baslik="Takılma süreleri">
      <dl className="flex flex-col gap-2 text-sm">
        {TAKILMA_SURELERI.map((s) => (
          <div key={s.ne} className="flex justify-between gap-3">
            <dt className="text-muted-foreground">{s.ne}</dt>
            <dd className="text-right font-medium text-ana">{s.sure}</dd>
          </div>
        ))}
      </dl>
    </YanKutu>
  );
}

function TaramaOzeti({ sonuc }: { sonuc: TaramaSonucu }) {
  const turler = Object.entries(sonuc.olaylar);
  return (
    <p className="text-sm text-pretty" role="status">
      {turler.length === 0
        ? "Yeni hatırlatma gerekmedi: takılan bir süreç yok ya da hatırlatma zaten gönderilmişti."
        : `${sonuc.bildirim} hatırlatma gönderildi. ${turler
            .map(([tur, sayi]) => `${turEtiketi(tur)}: ${sayi}`)
            .join(", ")}.`}
      <span className="ml-1 text-xs text-muted-foreground">
        ({sonuc.sure_sn} sn)
      </span>
    </p>
  );
}

export function PasifBaglantilar({
  pasifler,
}: {
  pasifler: PasifBaglanti[] | null;
}) {
  return (
    <PanelBolumu
      id="pasifler"
      baslik="Şu an takılanlar"
      aciklama="Süresi dolmuş ve hâlâ ilerlemeyen süreçler; en uzun süredir bekleyen en üstte. Bu listeyi açmak kimseye hatırlatma göndermez."
    >
      {pasifler === null ? null : pasifler.length === 0 ? (
        <BosDurum metin="Şu an takılan bir süreç yok." />
      ) : (
        <ul className={LISTE}>
          {pasifler.map((pasif) => (
            <PasifSatiri
              key={`${pasif.eslesme_id}-${pasif.tur}-${pasif.adim ?? ""}`}
              pasif={pasif}
            />
          ))}
        </ul>
      )}
    </PanelBolumu>
  );
}

function PasifSatiri({ pasif }: { pasif: PasifBaglanti }) {
  return (
    <li className={SATIR}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <DurumEtiketi metin={turEtiketi(pasif.tur)} />
        <span className="text-sm">
          {pasif.genc_adi} · {pasif.kurum_adi}
        </span>
        {pasif.isbirligi_id ? (
          <Link
            href={`/isbirligi/${pasif.isbirligi_id}`}
            className="ml-auto text-sm text-baglanti underline underline-offset-4"
          >
            İş birliğini aç
          </Link>
        ) : null}
      </div>
      <p className="text-sm text-pretty text-muted-foreground">
        {pasifSureMetni(pasif.tur, pasif.gun)}
        {pasif.adim ? ` · “${pasif.adim}”` : ""} · hatırlatma gidecek kişi:{" "}
        {alicilarMetni(pasif.alicilar)} ·{" "}
        {pasif.son_hatirlatma
          ? `son hatırlatma ${tarihYaz(pasif.son_hatirlatma, true)}`
          : "henüz hatırlatılmadı"}
      </p>
    </li>
  );
}

export function SonHatirlatmalar({
  olaylar,
}: {
  olaylar: CanlilikOlayi[] | null;
}) {
  return (
    <PanelBolumu id="olaylar" baslik="Son hatırlatmalar">
      {olaylar === null ? null : olaylar.length === 0 ? (
        <BosDurum metin="Henüz hatırlatma gönderilmedi. Kontrolden sonra gönderilenler burada görünür." />
      ) : (
        <ul className={LISTE}>
          {olaylar.map((olay) => (
            <li key={olay.id} className={SATIR}>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <DurumEtiketi metin={turEtiketi(olay.tur)} />
                <span className="text-sm">
                  {olay.alici_adi ?? "—"}
                  {olay.alici_rol ? (
                    <span className="text-muted-foreground">
                      {" "}
                      ({olay.alici_rol === "genc" ? "genç" : "firma"})
                    </span>
                  ) : null}
                </span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {tarihYaz(olay.tetiklenme_tarihi, true)}
                </span>
              </div>
              {olay.mesaj_metni ? (
                <p className="text-sm text-pretty text-muted-foreground">
                  {olay.mesaj_metni}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </PanelBolumu>
  );
}
