"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

import { SayfaDurumu } from "@/components/sayfa";

/**
 * İhtiyaç düzenleme artık firma panelinde sağdan açılan panelde (docs/kararlar.md
 * D1, F21). Eski adres (bildirimler, e-postalar, yer imleri) panele yönlenir.
 */
export default function IlanDuzenlemeYonlendirmesi() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/kurum?duzenle=${encodeURIComponent(id)}`);
  }, [id, router]);
  return <SayfaDurumu />;
}
