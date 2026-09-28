/**
 * KVKK aydınlatma metni (docs/plans/genc-akisi.md § 5.1).
 *
 * İçerik platformun gerçekte ne topladığını ve ne yaptığını anlatıyor; hukuki
 * gözden geçirmeden geçmedi. Yayına almadan önce veri sorumlusunun (GİRVAK)
 * onayladığı metinle değiştirilmeli. Kayıt formundaki onay kutusu buraya bağlı.
 */

const BOLUMLER: { baslik: string; maddeler: string[] }[] = [
  {
    baslik: "Hangi verileri topluyoruz",
    maddeler: [
      "Kimlik ve iletişim: ad soyad, e-posta adresi.",
      "Çalışma tercihleri: şehir, çalışma modeli (uzaktan, hibrit, iş yerinde), müsaitlik ve başlangıç tarihi.",
      "Eğitim ve durum: öğrenci, mezun ya da çalışıyor; isteğe bağlı olarak okul, bölüm, sınıf, mezuniyet yılı.",
      "İsteğe bağlı bağlantılar: GitHub, LinkedIn, portfolyo adresi.",
      "Yetenek kartın: Keşif sohbetinde anlattığın işler, araçlar, kanıt linkleri ve belirttiğin referans kişilerin e-posta adresleri.",
    ],
  },
  {
    baslik: "Hangi verileri bilinçli olarak toplamıyoruz",
    maddeler: [
      "Fotoğraf, yaş ya da doğum tarihi, cinsiyet, medeni durum, TC kimlik numarası, adres ve ücret beklentisi. Eşleştirme yalnızca yetkinliğe dayanır.",
    ],
  },
  {
    baslik: "Ne için kullanıyoruz",
    maddeler: [
      "Yetenek kartını oluşturmak ve kurumların ihtiyaçlarıyla eşleştirmek.",
      "Kanıtlarını ve referans yanıtlarını değerlendirip kartında güven göstergesi olarak göstermek.",
      "Eşleşme, iş birliği ve hatırlatmalarla ilgili uygulama içi bildirim göndermek.",
      "Programın hedeflerini ölçmek (yalnızca toplu sayılar; kişisel veri içermez).",
    ],
  },
  {
    baslik: "Kim görür",
    maddeler: [
      "Adın ve yetenek kartın, eşleştiğin kurumlara görünür.",
      "E-posta adresin yalnızca karşılıklı ilgi oluştuğunda (bir kurumun ilgisini kabul ettiğinde ya da ilgi gösterdiğin kurum da ilgilendiğinde) ve yalnızca o kurumla paylaşılır.",
      "Referans kişinin e-posta adresi kurumlarla paylaşılmaz.",
    ],
  },
  {
    baslik: "Hakların",
    maddeler: [
      "Profilini ve kartını istediğin zaman düzenleyebilirsin.",
      "Verilerinle ilgili bilgi, düzeltme ya da silme talebi için program ekibine başvurabilirsin.",
    ],
  },
];

export default function KvkkSayfasi() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          KVKK aydınlatma metni
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Zemin360 platformunda kişisel verilerinin nasıl işlendiğini burada
          anlatıyoruz.
        </p>
      </header>
      {BOLUMLER.map((bolum) => (
        <section key={bolum.baslik} className="flex flex-col gap-2">
          <h2 className="font-heading text-lg font-semibold text-ana">
            {bolum.baslik}
          </h2>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-pretty">
            {bolum.maddeler.map((madde) => (
              <li key={madde}>{madde}</li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
