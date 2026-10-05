/**
 * KVKK aydınlatma metni (docs/plans/genc-akisi.md § 5.1).
 *
 * İçerik platformun gerçekte ne topladığını ve ne yaptığını anlatıyor; hukuki
 * gözden geçirmeden geçmedi. Yayına almadan önce veri sorumlusunun (GİRVAK)
 * onayladığı metinle değiştirilmeli. Kayıt formundaki onay kutusu buraya bağlı.
 */

import { Sayfa, SayfaBasligi } from "@/components/sayfa";

const BOLUMLER: { baslik: string; maddeler: string[] }[] = [
  {
    baslik: "Hangi verileri topluyoruz",
    maddeler: [
      "Kimlik ve iletişim: ad soyad, e-posta adresi.",
      "Çalışma tercihleri: şehir, çalışma modeli (uzaktan, hibrit, iş yerinde), müsaitlik ve başlangıç tarihi.",
      "Eğitim ve durum: öğrenci, mezun ya da çalışıyor; isteğe bağlı olarak okul, bölüm, sınıf, mezuniyet yılı.",
      "İsteğe bağlı bağlantılar: GitHub, LinkedIn, portfolyo adresi.",
      "Yetenek kartın: Keşif sohbetinde anlattığın işler, araçlar, kanıt linkleri ve belirttiğin referans kişilerin e-posta adresleri.",
      "Kanıt olarak yüklediğin PDF ve görseller ile içlerinden okunan metin. Okunan metinde T.C. kimlik numarası, telefon ve adres maskelenerek saklanır; görselin konum ve cihaz bilgisi (EXIF) silinir.",
    ],
  },
  {
    baslik: "Hangi verileri bilinçli olarak toplamıyoruz",
    maddeler: [
      "Fotoğraf, yaş ya da doğum tarihi, cinsiyet, medeni durum, TC kimlik numarası, adres ve ücret beklentisi. Eşleştirme yalnızca yetkinliğe dayanır. Yüklediğin bir belgede bunlar yazıyorsa okunan metinde maskelenir ve eşleştirmede kullanılmaz.",
    ],
  },
  {
    baslik: "Ne için kullanıyoruz",
    maddeler: [
      "Yetenek kartını oluşturmak ve firmaların ihtiyaçlarıyla eşleştirmek.",
      "Kanıtlarını ve referans yanıtlarını değerlendirip kartında güven göstergesi olarak göstermek.",
      "Referans gösterdiğin kişiye adını ve çalışmanın başlığını içeren bir yanıt isteği e-postası (ve yanıt gelmezse bir hatırlatma) göndermek.",
      "Eşleşme, iş birliği ve hatırlatmalarla ilgili uygulama içi bildirim göndermek.",
      "Programın hedeflerini ölçmek (yalnızca toplu sayılar; kişisel veri içermez).",
    ],
  },
  {
    baslik: "Kim görür",
    maddeler: [
      "Adın ve yetenek kartın, eşleştiğin firmalara görünür.",
      "E-posta adresin yalnızca karşılıklı ilgi oluştuğunda (bir firmanın ilgisini kabul ettiğinde ya da ilgi gösterdiğin firma da ilgilendiğinde) ve yalnızca o firmayla paylaşılır.",
      "Referans kişinin e-posta adresi firmalarla paylaşılmaz.",
      "Yüklediğin dosyaları yalnızca sen ve GİRVAK görür; firmalar yalnızca değerlendirme sonucunu görür. İstersen dosya başına “Firmalar görebilir” seçeneğini açabilirsin.",
      "e-Devlet belgesi yüklersen GİRVAK belgeyi barkoduyla turkiye.gov.tr üzerinden elle doğrular.",
    ],
  },
  {
    baslik: "Hizmet sağlayıcılar ve yurt dışına aktarım",
    maddeler: [
      "Google (Gemini): sohbetlerin, kanıt linklerinin içeriği ve yüklediğin dosyalar değerlendirme için işlenir.",
      "Voyage AI: kartının ve kanıtlarının metni eşleştirme için sayısal temsile çevrilir.",
      "Cloudflare R2: yüklediğin dosyalar özel bir depoda saklanır.",
      "Resend: doğrulama ve referans e-postaları bu servisle gönderilir.",
      "Bu sağlayıcıların sunucuları yurt dışındadır; veriler yalnızca yukarıdaki amaçlarla aktarılır.",
    ],
  },
  {
    baslik: "Hakların",
    maddeler: [
      "Profilini ve kartını istediğin zaman düzenleyebilirsin.",
      "Bir kanıtı ya da çalışmayı silince yüklediğin dosya da depodan silinir.",
      "Verilerinle ilgili bilgi, düzeltme ya da silme talebi için program ekibine başvurabilirsin.",
    ],
  },
];

export default function KvkkSayfasi() {
  return (
    <Sayfa>
      <SayfaBasligi
        baslik="KVKK aydınlatma metni"
        aciklama="Zemin360 platformunda kişisel verilerinin nasıl işlendiğini burada anlatıyoruz."
      />
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
    </Sayfa>
  );
}
