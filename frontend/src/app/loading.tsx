import { Sayfa } from "@/components/sayfa";
import { SayfaIskeleti } from "@/components/ui/iskelet";

/** Sayfa geçişlerinde, içerik gelene kadar. */
export default function Yukleniyor() {
  return (
    <Sayfa>
      <SayfaIskeleti />
    </Sayfa>
  );
}
