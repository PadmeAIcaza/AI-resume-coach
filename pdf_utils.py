from io import BytesIO # this is used for files that are not on your local computer. Flask gives you the file as raw bytes. BytesIO converts those bytes into something that behaves like a file
from pypdf import PdfReader # this library understands pdf files

MAX_PDF_PAGES = 5
MAX_RESUME_TEXT_LENGTH = 30000


class ResumeUploadError(ValueError): # ValueError is a custom exception
    """An upload error that is safe to display to the user."""


def extract_pdf_text(upload) -> str: # extract_pdf_text(resume_file)
    filename = (upload.filename or "").strip()
    if not filename: # if filename == "" (empty)
        raise ResumeUploadError("Please select a PDF resume.")
    if not filename.lower().endswith(".pdf"): # turns all the filename into lower capital letters and then checks if it is a PDF (ends with .pdf)
        raise ResumeUploadError("The resume file must have a .pdf extension.")

    pdf_bytes = upload.read() # reads the files and returns the text as bytes
    if not pdf_bytes: # if file is empty
        raise ResumeUploadError("The uploaded PDF is empty.")
    if b"%PDF-" not in pdf_bytes[:1024]: # b"%PDF-" means is a byte object. This looks at the first 1024 bytes (all valid pdf files begin with %PDF)
        raise ResumeUploadError("The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False) # converts the bytes into somehting that behaves as a file. strict=False allows PdfReader to be more "forgiving" (it doesnt get bitchy with formatting problems)
        if reader.is_encrypted:
            raise ResumeUploadError("Password-protected PDFs are not supported. Upload an unlocked PDF.")
        if not reader.pages:
            raise ResumeUploadError("The PDF does not contain any pages.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ResumeUploadError(f"The PDF has too many pages. The maximum is {MAX_PDF_PAGES}.")

        # extracts all the text in each page and append it to page_text (as a list of strings)
        page_text = [page.extract_text() or "" for page in reader.pages]
    except ResumeUploadError:
        raise
    except Exception: # catches every possible exception
        raise ResumeUploadError("The PDF could not be read. It may be damaged or use an unsupported format.") from None # from None hides the traceback. Users dont need to see all that

    # combine all strings in page_text into one string
    text = "\n\n".join(part.strip() for part in page_text if part.strip()).strip() # part.strip() ignores empty strings. "\n\n" adds blank lines between spaces
    if not text:
        raise ResumeUploadError("No selectable text was found. This may be a scanned or image-only PDF.")
    if len(text) > MAX_RESUME_TEXT_LENGTH:
        raise ResumeUploadError("The extracted resume is too long. Please upload a shorter PDF.")
    return text
