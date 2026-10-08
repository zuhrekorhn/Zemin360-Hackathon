/**
 * Kullanıcının yazdığı adın gösterimi: kelimelerin ilk harfi büyük ("zhre
 * korhan" → "Zhre Korhan"). Kayıt olduğu gibi saklanır; yalnızca ekranda.
 */
export function adGosterimi(ad: string): string {
  return ad
    .trim()
    .split(/\s+/)
    .map((kelime) =>
      kelime ? kelime.charAt(0).toLocaleUpperCase("tr") + kelime.slice(1) : "",
    )
    .join(" ");
}
