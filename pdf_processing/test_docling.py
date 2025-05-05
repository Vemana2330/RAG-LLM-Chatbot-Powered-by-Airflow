try:
    from docling.document_converter import PdfFormatOption
    print("✅ PdfFormatOption exists in 'docling.document_converter'")
    import inspect
    print("📍 Defined at:", inspect.getfile(PdfFormatOption))
except ImportError as e:
    print("❌ ImportError:", e)
except Exception as e:
    print("⚠️ Unexpected error:", e)
