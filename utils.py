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

def open_img(path:str, mode:Literal["pil", "b64"]="pil"):
    pil_image = Image.open(path)
    
    if mode == "b64":
        base64_image = pil_to_b64(pil_image)
        return base64_image
    else:
        return pil_image
    