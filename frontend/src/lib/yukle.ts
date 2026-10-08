"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { type Hata, hatayaCevir } from "@/lib/hata";

/**
 * Sayfa açılırken bir kez okunan veri: yanıt, hata ve yeniden okuma tek yerde.
 *
 * `oku` kararlı olmalı (modül düzeyinde bir api fonksiyonu ya da `useCallback`);
 * her çizimde yeni bir fonksiyon verilirse okuma tekrar tekrar tetiklenir. Kapı
 * (`GirisKapisi`) açılmadan çalışmaz, çünkü sayfa kapının içinde çizilir.
 */
export function useYukle<T>(oku: () => Promise<T>) {
  const [veri, setVeri] = useState<T | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const ilkOkuma = useRef(false);

  const yenile = useCallback(async () => {
    setHata(null);
    try {
      setVeri(await oku());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [oku]);

  useEffect(() => {
    if (ilkOkuma.current) return;
    ilkOkuma.current = true;
    void yenile();
  }, [yenile]);

  return { veri, hata, yenile };
}
