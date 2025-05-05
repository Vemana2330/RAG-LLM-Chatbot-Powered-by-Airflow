import io
import os
import logging
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
 
from dotenv import load_dotenv
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode, PictureItem
 
import boto3
 
# Load AWS credentials
load_dotenv()
 
AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
 
# Setup logging
logging.basicConfig(filename="docling_conversion.log", level=logging.INFO, format="%(message)s")
 
# S3 client
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)
 
def upload_to_s3(bucket, key, data_bytes):
    s3.upload_fileobj(io.BytesIO(data_bytes), bucket, key)
    logging.info(f"✅ Uploaded to s3://{bucket}/{key}")
 
def convert_pdf_to_markdown(pdf_bytes: bytes, year: str, quarter: str):
    pipeline_opts = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        generate_page_images=True,
        generate_picture_images=True,
        images_scale=2.0
    )
 
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)}
    )
 
    with NamedTemporaryFile(suffix=".pdf", delete=True) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf.flush()
 
        result = converter.convert(tmp_pdf.name)
        doc_stem = result.input.file.stem
        base_path = f"docling_markdown/{year}/{quarter}"
 
        # 1. Generate markdown (with image placeholders)
        markdown = result.document.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER)
 
        # 2. Upload images and replace placeholders
        image_count = 0
        for elem, _ in result.document.iterate_items():
            if isinstance(elem, PictureItem):
                image_count += 1
                with NamedTemporaryFile(suffix=".png", delete=True) as tmp_img:
                    elem.get_image(result.document).save(tmp_img, "PNG")
                    tmp_img.flush()
 
                    img_filename = f"image_{image_count}.png"
                    img_key = f"{base_path}/Images/{img_filename}"
 
                    with open(tmp_img.name, "rb") as img_data:
                        upload_to_s3(AWS_BUCKET, img_key, img_data.read())
 
                    # Generate public S3 URL
                    img_url = f"https://{AWS_BUCKET}.s3.amazonaws.com/{img_key}"
 
                    # Replace placeholder with actual image reference
                    markdown = markdown.replace("<!-- image -->", f"![{img_filename}]({img_url})", 1)
 
        # 3. Upload final markdown with actual image links
        markdown_key = f"{base_path}/{quarter}.md"
        upload_to_s3(AWS_BUCKET, markdown_key, markdown.encode("utf-8"))
 
        return {
            "markdown_s3_path": markdown_key,
            "images_uploaded": image_count,
            "preview_url": f"https://{AWS_BUCKET}.s3.amazonaws.com/{markdown_key}"
        }