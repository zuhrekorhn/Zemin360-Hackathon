import Link from "next/link";

import {
  BosDurum,
  DurumEtiketi,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import type { CanlilikOlayi, PasifBaglanti, TaramaSonucu } from "@/lib/api";
import { alicilarMetni, pasifSureMetni, turEtiketi } from "@/lib/canlilik";
import { cn } from "@/lib/utils";

const LISTE =
  "flex flex-col divide-y divide-kenar overflow-hidden rounded-xl border border-kenar bg-card";

/** "Taramayı şimdi çalıştır" ve son çalıştırmanın özeti. */
export function TaramaBolumu({
  taraniyor,
  sonuc,
  onCalistir,
}: {
  taraniyor: boolean;
  sonuc: TaramaSonucu | null;
  onCalistir: () => void;
}) {
  return (
    <PanelBolumu
      id="tarama"
      baslik="Canlılık taraması"
      aciklama="Hareketsiz kalan öneri, ilgi, plan ve adımlar için ilgili kişiye bir hatırlatma bırakır; aynı dönemde aynı hatırlatmayı tekrarlamaz. Canlıda bu işi zamanlanmış görev günde iki kez yapar."
    >
      <div
        className={cn(
          KUTU,
          "flex flex-wrap items-center gap-x-4 gap-y-3 px-6 py-5",
        )}
      >
        <Button
          type="button"
          size="lg"
          disabled={taraniyor}
          onClick={onCalistir}
        >
          {taraniyor ? "Taranıyor…" : "Taramayı şimdi çalıştır"}
        </Button>
        {sonuc ? <TaramaOzeti sonuc={sonuc} /> : null}
      </div>
    </PanelBolumu>
  );
}

function TaramaOzeti({ sonuc }: { sonuc: TaramaSonucu }) {
  const turler = Object.entries(sonuc.olaylar);
  return (
    <p className="text-sm text-pretty" role="status">
      {turler.length === 0
        ? "Yeni hatırlatma yok: hareketsizlik süresini aşan kayıt yok ya da bu dönemde zaten hatırlatıldı."
        : `${sonuc.bildirim} bildirim gönderildi. ${turler
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
      baslik="Pasifleşen bağlantılar"
      aciklama="Şu an hareketsizlik süresini aşmış kayıtlar; en uzun süredir hareketsiz olan önce. Bu liste okunurken hiçbir hatırlatma gönderilmez."
    >
      {pasifler === null ? null : pasifler.length === 0 ? (
        <BosDurum metin="Şu an hareketsizlik süresini aşmış bir bağlantı yok." />
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
    <li className="flex flex-col gap-1 px-5 py-4">
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
        {pasif.adim ? ` · “${pasif.adim}”` : ""} · hatırlatılacak:{" "}
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
        <BosDurum metin="Henüz hatırlatma gönderilmedi. Tarama çalıştığında burada görünür." />
      ) : (
        <ul className={LISTE}>
          {olaylar.map((olay) => (
            <li key={olay.id} className="flex flex-col gap-1 px-5 py-4">
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
