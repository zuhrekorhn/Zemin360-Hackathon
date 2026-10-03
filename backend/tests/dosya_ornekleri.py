"""Testlerde kullanılan küçük PDF ve görsel örnekleri (bellekte üretilir)."""

import io

import pikepdf
from PIL import Image


def pdf(*, javascript: bool = False, ek_dosya: bool = False) -> bytes:
    belge = pikepdf.new()
    belge.add_blank_page()
    if javascript:
        belge.Root.OpenAction = pikepdf.Dictionary(
            S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(1)")
        )
    if ek_dosya:
        belge.attachments["gizli.exe"] = pikepdf.AttachedFileSpec(belge, b"MZ")
    cikti = io.BytesIO()
    belge.save(cikti, deterministic_id=True)
    return cikti.getvalue()


def gorsel(bicim: str = "PNG", *, exif: bool = False, boyut=(8, 8)) -> bytes:
    resim = Image.new("RGB", boyut, (200, 30, 30))
    ek = {}
    if exif:
        veri = Image.Exif()
        veri[0x010F] = "Telefonum"  # Make
        veri[0x0131] = "Duzenleyici 1.0"  # Software
        ek["exif"] = veri.tobytes()
    cikti = io.BytesIO()
    resim.save(cikti, format=bicim, **ek)
    return cikti.getvalue()


def metinli_pdf(satirlar: list[str]) -> bytes:
    """Metin katmanı olan tek sayfalık PDF (ASCII satırlar)."""
    belge = pikepdf.new()
    sayfa = belge.add_blank_page(page_size=(612, 792))
    sayfa.Resources = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(
            F1=pikepdf.Dictionary(
                Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica
            )
        )
    )
    akis = (
        "BT /F1 11 Tf 72 720 Td 14 TL "
        + " ".join(f"({s.replace('(', '').replace(')', '')}) '" for s in satirlar)
        + " ET"
    )
    sayfa.Contents = belge.make_stream(akis.encode("latin-1"))
    cikti = io.BytesIO()
    belge.save(cikti, deterministic_id=True)
    return cikti.getvalue()


def imzali_pdf(satirlar: list[str], imzalayan: str = "Ornek Universitesi"):
    """Kendinden imzalı sertifikayla PAdES imzalı PDF. Döner: (pdf, asn1 sertifika)."""
    import datetime as dt

    from asn1crypto import keys, x509
    from cryptography import x509 as cx509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko_certvalidator.registry import SimpleCertificateStore

    anahtar = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ad = cx509.Name([cx509.NameAttribute(NameOID.COMMON_NAME, imzalayan)])
    simdi = dt.datetime.now(dt.UTC)
    sertifika = (
        cx509.CertificateBuilder()
        .subject_name(ad)
        .issuer_name(ad)
        .public_key(anahtar.public_key())
        .serial_number(cx509.random_serial_number())
        .not_valid_before(simdi - dt.timedelta(days=1))
        .not_valid_after(simdi + dt.timedelta(days=30))
        .add_extension(cx509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            cx509.KeyUsage(True, True, False, False, False, True, False, False, False),
            critical=True,
        )
        .sign(anahtar, hashes.SHA256())
    )
    asn1_sertifika = x509.Certificate.load(sertifika.public_bytes(serialization.Encoding.DER))
    asn1_anahtar = keys.PrivateKeyInfo.load(
        anahtar.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    imzaci = signers.SimpleSigner(
        signing_cert=asn1_sertifika,
        signing_key=asn1_anahtar,
        cert_registry=SimpleCertificateStore.from_certs([asn1_sertifika]),
    )
    yazici = IncrementalPdfFileWriter(io.BytesIO(metinli_pdf(satirlar)))
    cikti = signers.sign_pdf(yazici, signers.PdfSignatureMetadata(field_name="Imza"), signer=imzaci)
    return cikti.getvalue(), asn1_sertifika
