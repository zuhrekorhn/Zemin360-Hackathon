"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { Mesaj, SohbetHatasi } from "@/components/sohbet";
import {
  type GencProfili,
  type KartTaslagi,
  type YetenekKartiYaniti,
  ApiHatasi,
  kartOnayla,
  sohbetBaslat,
  sohbetCevap,
  sohbetDevam,
} from "@/lib/api";
import { hatayaCevir } from "@/lib/hata";
import { kayitliSohbet, sohbetiKaydet, sohbetiUnut } from "@/lib/kesif-oturumu";
import { useOturum } from "@/lib/oturum";

/**
 * Keşif sohbetinin durum makinesi (docs/agent-specs.md § 1): başlatılıyor →
 * sohbet → taslak → kaydedildi. Görünüm app/kesif/page.tsx'te; burada
 * yalnızca durum ve backend çağrıları.
 *
 * Taslak onaylanana kadar hiçbir şey veritabanına yazılmaz (insan onayı).
 */

export type Asama = "baslatiliyor" | "sohbet" | "taslak" | "kaydedildi";

export function useKesifSohbeti() {
  const { tazele } = useOturum();
  const [asama, setAsama] = useState<Asama>("baslatiliyor");
  const [oturumId, setOturumId] = useState<string | null>(null);
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [taslak, setTaslak] = useState<KartTaslagi | null>(null);
  const [kart, setKart] = useState<YetenekKartiYaniti | null>(null);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);
  // 429 sonrası "Tekrar dene" aynı cevabı yeniden göndersin diye tutuluyor;
  // sohbet backend'de checkpointer'da durduğu için oturum_id değişmez.
  const bekleyenCevap = useRef<string | null>(null);
  const baslatildi = useRef(false);

  // Hata cümlesi tek yerden: lib/hata.ts (429 hız sınırı, 503 arıza ayrımı orada).
  const hatayiYaz = useCallback(
    (sebep: unknown) => setHata(hatayaCevir(sebep)),
    [],
  );

  const baslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      // Yarım kalmış sohbet varsa kaldığı yerden sürer (yenileme, sekme kapanması).
      const eski = kayitliSohbet();
      if (eski) {
        try {
          const devam = await sohbetDevam(eski);
          setOturumId(devam.oturum_id);
          setMesajlar(devam.mesajlar);
          setTaslak(devam.taslak);
          setAsama(devam.taslak_hazir ? "taslak" : "sohbet");
          return;
        } catch (sebep) {
          // Başka hesabın ya da silinmiş sohbet (404): unut ve yenisini aç.
          // Başka bir hata (ağ, sunucu) gerçek hatadır, yeni sohbetle örtülmez.
          if (!(sebep instanceof ApiHatasi && sebep.durumKodu === 404))
            throw sebep;
          sohbetiUnut();
        }
      }
      const yanit = await sohbetBaslat();
      sohbetiKaydet(yanit.oturum_id);
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
      setAsama("sohbet");
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }, [hatayiYaz]);

  useEffect(() => {
    // React StrictMode geliştirmede efekti iki kez çalıştırıyor; ikinci bir
    // oturum açılmasın.
    if (baslatildi.current) return;
    baslatildi.current = true;
    void baslat();
  }, [baslat]);

  async function cevapGonder(cevap: string) {
    if (!oturumId || !cevap.trim()) return;

    setHata(null);
    setBekleniyor(true);
    bekleyenCevap.current = cevap;

    try {
      const yanit = await sohbetCevap(oturumId, cevap);
      bekleyenCevap.current = null;
      setTaslak(yanit.taslak);

      if (yanit.taslak_hazir) {
        setAsama("taslak");
      } else if (yanit.soru) {
        setMesajlar((oncekiler) => [
          ...oncekiler,
          { kim: "ajan", metin: yanit.soru as string },
        ]);
      }
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }

  /** Kullanıcının cevabı: balona hemen düşer, sonra backend'e gider. */
  function gonder(cevap: string) {
    const temiz = cevap.trim();
    if (!temiz || bekleniyor) return;
    setMesajlar((oncekiler) => [
      ...oncekiler,
      { kim: "kullanici", metin: temiz },
    ]);
    void cevapGonder(temiz);
  }

  function tekrarDene() {
    if (bekleyenCevap.current) {
      void cevapGonder(bekleyenCevap.current);
    } else if (!oturumId) {
      void baslat();
    }
  }

  async function onayla(profil: GencProfili, duzeltilmisTaslak: KartTaslagi) {
    if (!oturumId) return;
    setHata(null);
    setBekleniyor(true);
    try {
      setKart(await kartOnayla(oturumId, profil, duzeltilmisTaslak));
      sohbetiUnut();
      setAsama("kaydedildi");
      // Menüdeki "Kartım" yeni karta bağlansın (/me).
      void tazele();
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }

  return {
    asama,
    mesajlar,
    taslak,
    kart,
    setKart,
    bekleniyor,
    hata,
    gonder,
    tekrarDene,
    onayla,
  };
}
