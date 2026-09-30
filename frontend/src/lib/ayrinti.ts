/**
 * Backend'in hata gövdesindeki `detail`'i kullanıcıya gösterilecek cümleye çevirir.
 *
 * İki biçim var: uçların kendi cümlesi (`"detail": "..."`) ve FastAPI'nin şema
 * doğrulama hataları (`"detail": [{"msg": "...", "loc": [...]}]`, 422). İkincisi
 * okunmadığında kullanıcı yalnızca "İstek başarısız: 422" görüyordu.
 */
export function ayrintiyiOku(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return undefined;
  const mesajlar = detail
    .map((hata) =>
      hata && typeof hata === "object" && "msg" in hata
        ? String((hata as { msg: unknown }).msg)
        : null,
    )
    .filter((mesaj): mesaj is string => Boolean(mesaj))
    // Yalnızca kendi doğrulayıcılarımızın Türkçe cümleleri: Pydantic onların
    // başına "Value error, " ekliyor. Pydantic'in kendi İngilizce mesajları
    // ("Field required" vb.) gösterilmez (docs/icerik-rehberi.md § 5.4);
    // hiçbiri kalmazsa arayüz durum koduna göre Türkçe cümle kullanır.
    .filter((mesaj) => mesaj.startsWith("Value error, "))
    .map((mesaj) => mesaj.replace(/^Value error, /, ""));
  const tekil = [...new Set(mesajlar)];
  return tekil.length > 0 ? tekil.join(" · ") : undefined;
}
