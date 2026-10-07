"use client";

/**
 * Kilitli ad ve değişiklik talebi (docs/dogrulama.md § 6.3).
 *
 * E-posta doğrulanınca ad profilden değişmez: başkasının adını yazıp onun
 * çalışmalarını sahiplenmek kapanır. Değişiklik GİRVAK'a talep olarak gider;
 * sonuç bildirim olarak gelir. Bekleyen talep varken yenisi istenmez.
 */

import { useState } from "react";

import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type GencProfil, adDegisikligiIste } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";

export function KilitliAd({
  profil,
  onTalep,
}: {
  profil: GencProfil;
  onTalep: (yeni: GencProfil) => void;
}) {
  const [acik, setAcik] = useState(false);
  const [yeniAd, setYeniAd] = useState("");
  const [gerekce, setGerekce] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);

  async function gonder() {
    if (!yeniAd.trim() || bekleniyor) return;
    setHata(null);
    setBekleniyor(true);
    try {
      onTalep(await adDegisikligiIste(yeniAd.trim(), gerekce.trim() || null));
      setAcik(false);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <FormAlani etiket="Adın" htmlFor="ad">
        <Input id="ad" value={profil.ad} disabled autoComplete="name" />
      </FormAlani>
      {profil.bekleyen_ad ? (
        <p className="text-sm text-muted-foreground text-pretty" role="status">
          Ad değişikliği talebin inceleniyor: “{profil.bekleyen_ad}”. Sonucu
          bildirim olarak göreceksin.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground text-pretty">
          E-postanı doğruladığın için adın kilitli; çalışmalarının sana ait
          olduğu bu adla gösteriliyor.{" "}
          {acik ? null : (
            <button
              type="button"
              onClick={() => setAcik(true)}
              className="text-baglanti underline"
            >
              Ad değişikliği iste
            </button>
          )}
        </p>
      )}
      {acik && !profil.bekleyen_ad ? (
        // Profil formunun içinde durduğu için ayrı <form> değil: Enter profili kaydetmesin.
        <div className="flex flex-col gap-3 rounded-sm border border-kenar p-4">
          <FormAlani etiket="Yeni adın" htmlFor="yeni-ad">
            <Input
              id="yeni-ad"
              value={yeniAd}
              maxLength={100}
              onChange={(olay) => setYeniAd(olay.target.value)}
            />
          </FormAlani>
          <FormAlani etiket="Neden?" htmlFor="ad-gerekce" istegeBagli>
            <Input
              id="ad-gerekce"
              value={gerekce}
              maxLength={300}
              placeholder="Örneğin: evlilik, yazım hatası"
              onChange={(olay) => setGerekce(olay.target.value)}
            />
          </FormAlani>
          {hata ? <HataKutusu hata={hata} /> : null}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              disabled={!yeniAd.trim() || bekleniyor}
              onClick={() => void gonder()}
            >
              {bekleniyor ? "Gönderiliyor…" : "Talebi gönder"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setAcik(false)}
            >
              Vazgeç
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
