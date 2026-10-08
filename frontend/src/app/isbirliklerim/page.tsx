"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { IsbirligiSatiri } from "@/components/isbirligi-satiri";
import { BosDurum } from "@/components/panel";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { type IsbirligiOzeti, isbirliklerim } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { hitapRolden, hitapla } from "@/lib/hitap";
import { isbirligiSirasi } from "@/lib/takip";

/**
 * İş birliklerim (docs/takip.md): kabul edilen her eşleşmenin iş birliği,
 * süren önce. Menüde genç için kendi sayfası; firma paneli aynı satırı kullanır.
 */
export default function IsbirliklerimSayfasi() {
  return (
    <GirisKapisi roller={["genc", "kurum"]}>
      <IsbirlikleriListesi />
    </GirisKapisi>
  );
}

function IsbirlikleriListesi() {
  const hesap = useGirisliHesap();
  const hitap = hitapRolden(hesap.rol);
  const [liste, setListe] = useState<IsbirligiOzeti[] | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setListe(isbirligiSirasi(await isbirliklerim()));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik={hitapla(hitap, "İş birliklerin", "İş birlikleriniz")}
        aciklama={hitapla(
          hitap,
          "Karşılıklı ilgiyle başlayan çalışmaların. Planı ve adımları her iki taraf birlikte onaylar.",
          "Karşılıklı ilgiyle başlayan çalışmalarınız. Planı ve adımları her iki taraf birlikte onaylar.",
        )}
      />

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      {liste === null ? (
        <ListeIskeleti />
      ) : liste.length === 0 ? (
        <BosDurum
          metin={hitapla(
            hitap,
            "Henüz iş birliğin yok. Bir firmayla karşılıklı ilgi oluştuğunda iş birliği burada açılır.",
            "Henüz iş birliğiniz yok. Bir adayla karşılıklı ilgi oluştuğunda iş birliği burada açılır.",
          )}
          eylem={
            hesap.rol === "genc"
              ? { href: "/genc", etiket: "Fırsatlara bak" }
              : undefined
          }
        />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {liste.map((isbirligi) => (
            <IsbirligiSatiri
              key={isbirligi.isbirligi_id}
              isbirligi={isbirligi}
            />
          ))}
        </ul>
      )}
    </Sayfa>
  );
}
