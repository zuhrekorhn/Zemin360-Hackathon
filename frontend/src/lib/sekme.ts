/**
 * Sekme listesinde klavyeyle gezinme (WAI-ARIA Tabs deseni).
 *
 * Sağ/sol ok bir sonraki/önceki sekmeye geçer ve uçlarda başa sarar;
 * Home ilk, End son sekmeye gider. Başka bir tuş gezinme değildir: null
 * döner, çağıran olayı olduğu gibi bırakır (Tab ile panele geçilebilsin).
 */
export function klavyeyleSekme(
  anlik: number,
  tus: string,
  sayi: number,
): number | null {
  if (sayi <= 0) return null;
  switch (tus) {
    case "ArrowRight":
      return (anlik + 1) % sayi;
    case "ArrowLeft":
      return (anlik - 1 + sayi) % sayi;
    case "Home":
      return 0;
    case "End":
      return sayi - 1;
    default:
      return null;
  }
}
