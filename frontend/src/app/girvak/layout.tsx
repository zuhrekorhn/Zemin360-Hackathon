import { GirisKapisi } from "@/components/giris-kapisi";

/** GİRVAK'ın bütün sayfaları aynı kapıdan geçer; sayfalar arasında kapı yeniden çizilmez. */
export default function GirvakDuzeni({
  children,
}: {
  children: React.ReactNode;
}) {
  return <GirisKapisi roller={["girvak"]}>{children}</GirisKapisi>;
}
