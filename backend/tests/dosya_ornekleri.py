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
    belge.save(cikti)
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
