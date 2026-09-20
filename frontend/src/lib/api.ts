/**
 * Backend (FastAPI) ile konuşan ince bir fetch sarmalayıcısı.
 * Endpoint listesi: docs/api-contracts.md
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiHatasi extends Error {
  constructor(
    message: string,
    readonly durumKodu?: number,
  ) {
    super(message);
    this.name = "ApiHatasi";
  }
}

export async function apiIstek<T>(
  yol: string,
  secenekler: RequestInit = {},
): Promise<T> {
  let yanit: Response;

  try {
    yanit = await fetch(`${API_URL}${yol}`, {
      ...secenekler,
      headers: {
        "Content-Type": "application/json",
        ...secenekler.headers,
      },
    });
  } catch {
    // Ağ hatası / backend ayakta değil / CORS engeli
    throw new ApiHatasi(`Backend'e ulaşılamadı (${API_URL})`);
  }

  if (!yanit.ok) {
    throw new ApiHatasi(
      `İstek başarısız: ${yanit.status} ${yanit.statusText}`,
      yanit.status,
    );
  }

  return (await yanit.json()) as T;
}

export type SaglikYaniti = { status: string };

/** GET /health — backend ayakta mı? */
export function saglikKontrol(): Promise<SaglikYaniti> {
  return apiIstek<SaglikYaniti>("/health", { cache: "no-store" });
}

export { API_URL };
