# ✅ FILE: pdf_processing/mistral.py

import os
import io
import base64
import logging
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
from PIL import Image
from mistralai import Mistral
from mistralai import DocumentURLChunk
from mistralai.models import OCRResponse

# Load environment variables
load_dotenv()

AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

import boto3

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

logging.basicConfig(filename="mistral_conversion.log", level=logging.INFO, format="%(message)s")

def upload_to_s3(bucket, key, data_bytes):
    s3.upload_fileobj(io.BytesIO(data_bytes), bucket, key)
    logging.info(f"✅ Uploaded to s3://{bucket}/{key}")

def replace_image_references(md: str, images: dict, base_path: str) -> str:
    for img_id, img_base64 in images.items():
        img_data = base64.b64decode(img_base64.split(",")[-1])

        image_filename = f"{img_id}.png"
        s3_key = f"{base_path}/Images/{image_filename}"

        image = Image.open(io.BytesIO(img_data)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        upload_to_s3(AWS_BUCKET, s3_key, buffer.read())

        image_url = f"https://{AWS_BUCKET}.s3.amazonaws.com/{s3_key}"
        md = md.replace(f"![{img_id}]({img_id})", f"![{image_filename}]({image_url})")

    return md

def mistral_pdf_to_md(pdf_bytes: bytes, year: str, quarter: str):
    client = Mistral(api_key=MISTRAL_API_KEY)
    pdf_bytes_io = io.BytesIO(pdf_bytes)

    try:
        print("🔁 Uploading PDF to Mistral OCR...")
        uploaded = client.files.upload(file={"file_name": "temp.pdf", "content": pdf_bytes_io.read()}, purpose="ocr")
        print(f"✅ Upload complete: file_id = {uploaded.id}")
        
        signed_url = client.files.get_signed_url(file_id=uploaded.id, expiry=2)
        print(f"🔗 Signed URL fetched: {signed_url.url}")

        result = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
        print("✅ OCR processing successful")
    except Exception as e:
        print("❌ Error during Mistral processing:", str(e))
        raise e

    base_path = f"mistral_markdown/{year}/{quarter}"
    full_markdown = ""
    image_counter = 0

    for page in result.pages:
        images = {img.id: img.image_base64 for img in page.images}
        md_with_links = replace_image_references(page.markdown, images, base_path)
        full_markdown += md_with_links + "\n\n"
        image_counter += len(images)

    md_key = f"{base_path}/{quarter}.md"
    upload_to_s3(AWS_BUCKET, md_key, full_markdown.encode("utf-8"))

    return {
        "markdown_s3_path": md_key,
        "images_uploaded": image_counter,
        "preview_url": f"https://{AWS_BUCKET}.s3.amazonaws.com/{md_key}"
    }
