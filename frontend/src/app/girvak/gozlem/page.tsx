"use client";

import { GozlemPaneli } from "@/components/gozlem-paneli";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";

export default function GirvakGozlem() {
  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Gözlem"
        aciklama="Kanıt bağlantılarının erişilebilirliği ve dış servislerin durumu."
      />
      <GozlemPaneli />
    </Sayfa>
  );
}
