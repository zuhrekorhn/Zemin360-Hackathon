"use client";

import { GozlemPaneli } from "@/components/gozlem-paneli";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";

export default function GirvakGozlem() {
  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Sistem durumu"
        aciklama="Zemin360'ın dayandığı dış servislerin çalışıp çalışmadığı ve gençlerin eklediği kanıt linklerinin ne kadarının açılabildiği. Teknik bir sayfadır; her şey yolundaysa bakmanız gerekmez."
      />
      <GozlemPaneli />
    </Sayfa>
  );
}
