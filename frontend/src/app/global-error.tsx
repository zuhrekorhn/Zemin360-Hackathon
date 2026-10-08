"use client";

/**
 * Kök düzen bile çizilemediğinde son kalan sayfa. Tasarım belirteçleri ve
 * yazı tipleri yüklenemeyebilir, bu yüzden satır içi ve sistem yazı tipiyle;
 * renkler docs/design-language.md paletiyle aynı.
 */
export default function GenelHata({ reset }: { reset: () => void }) {
  return (
    <html lang="tr">
      <body
        style={{
          margin: 0,
          background: "#F3F4EE",
          color: "#16211B",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <main style={{ maxWidth: 480, margin: "0 auto", padding: "96px 20px" }}>
          <h1 style={{ margin: 0, fontSize: 28, color: "#1E3A2F" }}>
            Sayfa şu an açılamadı
          </h1>
          <p style={{ lineHeight: 1.6 }}>
            Beklenmedik bir sorun oluştu. Yeniden yüklemek çoğu zaman yeter.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              height: 40,
              padding: "0 20px",
              border: 0,
              borderRadius: 8,
              background: "#1E3A2F",
              color: "#F3F4EE",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Yeniden yükle
          </button>
        </main>
      </body>
    </html>
  );
}
