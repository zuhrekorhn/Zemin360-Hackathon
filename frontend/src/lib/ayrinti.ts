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
    // Pydantic kendi doğrulayıcılarımızın mesajının başına bunu ekliyor.
    .map((mesaj) => mesaj.replace(/^Value error, /, ""));
  const tekil = [...new Set(mesajlar)];
  return tekil.length > 0 ? tekil.join(" · ") : undefined;
}
