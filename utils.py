from typing import ByteString
import base64
from io import BytesIO
from typing import Literal
from PIL import Image

def pil_to_b64(img):
    buffer = BytesIO()
    img=img.convert("RGB")
    img.save(buffer, format="jpeg")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return base64_image

def byte_to_b64(file_bytes:ByteString):
    return base64.b64encode(file_bytes).decode()

def open_img(path: str, mode: Literal["pil", "b64", "bytes"] = "pil"):
    pil_image = Image.open(path)
    
    if mode == "b64":
        return pil_to_b64(pil_image)
    elif mode == "bytes":
        img_byte_arr = BytesIO()
        pil_image.save(img_byte_arr, format=pil_image.format)
        return img_byte_arr.getvalue()
    else:
        return pil_image