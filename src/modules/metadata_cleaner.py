import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from PIL import Image

from PyPDF2 import PdfReader, PdfWriter

from docx import Document

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC

from openpyxl import load_workbook

import piexif

try:
    from pptx import Presentation
    CAN_HANDLE_PPTX = True
except ImportError:
    CAN_HANDLE_PPTX = False

try:
    from odf.opendocument import load as odf_load
    CAN_HANDLE_ODF = True
except ImportError:
    CAN_HANDLE_ODF = False


def remove_metadata_from_zip(zip_path):
    """ 
    Unzip -> Remove metadata from each entry -> Re-zip.
    """
    temp_dir = "temp_zip_extract"
    try:
        logger.info(f"Processing ZIP: {zip_path}")
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                remove_metadata(file_path)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname=arc_name)

        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(temp_dir)

        return True
    except Exception as e:
        logger.exception(f"Error processing ZIP {zip_path}: {e}")
        return False


def remove_exif_jpeg(file_path):
    """ 
    Strip EXIF from JPEG without re-encoding 
    """
    try:
        logger.info(f"Stripping EXIF from JPEG: {file_path}")
        piexif.remove(file_path)
        # Verify removal
        exif_dict = piexif.load(file_path)
        if any(exif_dict[tag] for tag in ["0th", "Exif", "GPS", "1st"]):
            logger.info(f"EXIF still present after piexif.remove. Re-encoding: {file_path}")
            _reencode_jpeg(file_path)
        else:
            logger.info(f"EXIF successfully removed: {file_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing JPEG EXIF {file_path}: {e}")
        # Fallback to re-encode if piexif fails
        try:
            _reencode_jpeg(file_path)
            return True
        except Exception as ex:
            logger.exception(f"Failed to re-encode JPEG: {file_path}, error: {ex}")
            return False


def _reencode_jpeg(file_path):
    """
    Re-encode the JPEG with Pillow. This definitely strips EXIF,
    but may alter quality/size if not configured carefully.
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB (some images might be in different modes)
            rgb_img = img.convert("RGB")
            # Save, forcing 'exif' to be blank
            rgb_img.save(file_path, format='JPEG', exif=b'')
        logger.info(f"Re-encoded JPEG to remove residual EXIF: {file_path}")
    except Exception as e:
        logger.exception(f"Failed to re-encode JPEG: {file_path}, error: {e}")
        raise


def remove_metadata_from_jpeg(file_path):
    """
    Attempt to remove EXIF from JPEG using piexif (no re-encoding).
    If EXIF still remains, fallback to re-encoding with Pillow to ensure
    all metadata is stripped. This may alter quality/file size slightly.
    """
    try:
        remove_exif_jpeg(file_path)
        return True
    except Exception as e:
        logger.error(f"Failed to remove metadata from JPEG {file_path}: {e}")
        return False


def remove_metadata_from_image(image_path):
    """
    Images beyond JPEG (PNG, GIF, BMP, TIFF):
    Re-encode with Pillow to drop metadata.
    """
    ext = os.path.splitext(image_path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return remove_metadata_from_jpeg(image_path)
    try:
        logger.info(f"Processing image: {image_path}")
        with Image.open(image_path) as img:
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            # Keep the original format if possible
            clean_img.save(image_path, format=img.format)
        logger.info(f"Metadata removed from image: {image_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing image {image_path}: {e}")
        return False


def remove_metadata_from_pdf(pdf_path):
    """
    PDF: Read pages, rewrite them, omit doc info. 
    """
    try:
        logger.info(f"Processing PDF: {pdf_path}")
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with open(pdf_path, 'wb') as out_pdf:
            writer.write(out_pdf)
        logger.info(f"Metadata removed from PDF: {pdf_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing PDF {pdf_path}: {e}")
        return False


def remove_metadata_from_docx(docx_path):
    """
    DOCX: Clear core properties with python-docx.
    """
    try:
        logger.info(f"Processing DOCX: {docx_path}")
        doc = Document(docx_path)
        metadata_fields = [
            'author', 'comments', 'category', 'content_status',
            'identifier', 'keywords', 'language', 'last_modified_by',
            'last_printed', 'revision', 'subject', 'title', 'version'
        ]
        for prop in metadata_fields:
            try:
                setattr(doc.core_properties, prop, "")
            except ValueError:
                pass
        doc.settings.odd_and_even_pages_header_footer = False
        doc.save(docx_path)
        logger.info(f"Metadata removed from DOCX: {docx_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing DOCX {docx_path}: {e}")
        return False


def remove_metadata_from_pptx(pptx_path):
    """
    PPTX: Clear core properties with python-pptx.
    """
    if not CAN_HANDLE_PPTX:
        logger.warning("python-pptx not installed; cannot process PPTX.")
        return False
    try:
        logger.info(f"Processing PPTX: {pptx_path}")
        ppt = Presentation(pptx_path)
        props = ppt.core_properties
        props.author = ""
        props.category = ""
        props.comments = ""
        props.content_status = ""
        props.created = None
        props.identifier = ""
        props.keywords = ""
        props.last_modified_by = ""
        props.last_printed = None
        props.modified = None
        props.revision = ""
        props.subject = ""
        props.title = ""
        ppt.save(pptx_path)
        logger.info(f"Metadata removed from PPTX: {pptx_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing PPTX {pptx_path}: {e}")
        return False


def remove_metadata_from_ppt(ppt_path):
    """
    PPT (legacy):
    Typically convert .ppt -> .pptx, then do the PPTX route.
    """
    try:
        logger.warning(f".ppt is legacy binary; recommended to convert {ppt_path} to .pptx first.")
        return False
    except Exception as e:
        logger.exception(f"Error processing PPT {ppt_path}: {e}")
        return False


def remove_metadata_from_odt(odt_path):
    """
    ODT (OpenDocument Text): Use odfpy to remove <office:meta>.
    """
    if not CAN_HANDLE_ODF:
        logger.warning("odfpy not installed; cannot process ODT.")
        return False
    try:
        logger.info(f"Processing ODT: {odt_path}")
        doc = odf_load(odt_path)
        meta = doc.meta
        # ~(^-^)~ Remove all metadata children
        for child in list(meta.childNodes):
            meta.removeChild(child)
        doc.save(odt_path)
        logger.info(f"Metadata removed from ODT: {odt_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing ODT {odt_path}: {e}")
        return False


def remove_metadata_from_ods(ods_path):
    """
    ODS (OpenDocument Spreadsheet): Also via odfpy.
    """
    if not CAN_HANDLE_ODF:
        logger.warning("odfpy not installed; cannot process ODS.")
        return False
    try:
        logger.info(f"Processing ODS: {ods_path}")
        spreadsheet = odf_load(ods_path)
        meta = spreadsheet.meta
        for child in list(meta.childNodes):
            meta.removeChild(child)
        spreadsheet.save(ods_path)
        logger.info(f"Metadata removed from ODS: {ods_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing ODS {ods_path}: {e}")
        return False


def remove_metadata_from_epub(epub_path):
    """
    EPUB: Search for .opf files, remove <metadata> content.
    """
    temp_dir = "temp_epub_extract"
    try:
        logger.info(f"Processing EPUB: {epub_path}")
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        opf_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.opf'):
                    opf_files.append(os.path.join(root, file))

        import re
        for opf_file in opf_files:
            try:
                with open(opf_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                content = re.sub(r'<metadata[^>]*>.*?</metadata>', '<metadata></metadata>', content, flags=re.DOTALL)
                with open(opf_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Metadata stripped from OPF file: {opf_file}")
            except Exception as ex:
                logger.error(f"Could not strip metadata from {opf_file}: {ex}")

        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)
        logger.info(f"Re-zipped EPUB after metadata removal: {epub_path}")

        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(temp_dir)

        return True
    except Exception as e:
        logger.exception(f"Error processing EPUB {epub_path}: {e}")
        return False


def remove_metadata_from_rtf(rtf_path):
    r"""
    RTF: Naive \info removal with regex.
    """
    try:
        logger.info(f"Processing RTF: {rtf_path}")
        with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        import re
        content = re.sub(r'{\\info[^}]*}', '', content, flags=re.DOTALL)
        with open(rtf_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Metadata removed from RTF: {rtf_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing RTF {rtf_path}: {e}")
        return False


def remove_metadata_from_mp3(mp3_path):
    """ 
    MP3: Delete ID3 tags with mutagen.
    """
    try:
        logger.info(f"Processing MP3: {mp3_path}")
        audio = MP3(mp3_path, ID3=ID3)
        audio.delete()
        audio.save(mp3_path)
        logger.info(f"Metadata removed from MP3: {mp3_path}")
        return True
    except ID3NoHeaderError:
        try:
            audio = MP3(mp3_path)
            audio.save(mp3_path)
            logger.info(f"No ID3 header found, but file saved: {mp3_path}")
            return True
        except Exception as e:
            logger.exception(f"Error saving MP3 {mp3_path} without ID3 header: {e}")
            return False
    except Exception as e:
        logger.exception(f"Error processing MP3 {mp3_path}: {e}")
        return False


def remove_metadata_from_flac(flac_path):
    """ 
    FLAC: Remove tags with mutagen.
    """
    try:
        logger.info(f"Processing FLAC: {flac_path}")
        audio = FLAC(flac_path)
        audio.delete()
        audio.save()
        logger.info(f"Metadata removed from FLAC: {flac_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing FLAC {flac_path}: {e}")
        return False


def remove_metadata_from_xlsx(xlsx_path):
    """
    XLSX: Clear workbook properties with openpyxl.
    """
    try:
        logger.info(f"Processing XLSX: {xlsx_path}")
        workbook = load_workbook(filename=xlsx_path)
        metadata_fields = [
            'creator', 'title', 'subject', 'description',
            'keywords', 'category', 'comments', 'last_modified_by',
            'company', 'manager'
        ]
        for prop in metadata_fields:
            try:
                setattr(workbook.properties, prop, "")
            except ValueError:
                pass
        workbook.save(xlsx_path)
        logger.info(f"Metadata removed from XLSX: {xlsx_path}")
        return True
    except Exception as e:
        logger.exception(f"Error processing XLSX {xlsx_path}: {e}")
        return False

def remove_metadata(file_path):
    """ 
    Decide how to remove metadata based on file extension. 
    """
    logger.debug(f"File: {file_path}")
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        logger.error(f"Invalid file path type: {type(file_path).__name__}")
        return False
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
        return remove_metadata_from_image(file_path)

    elif file_extension == '.pdf':
        return remove_metadata_from_pdf(file_path)

    elif file_extension == '.docx':
        return remove_metadata_from_docx(file_path)

    elif file_extension == '.mp3':
        return remove_metadata_from_mp3(file_path)
    elif file_extension == '.flac':
        return remove_metadata_from_flac(file_path)

    elif file_extension == '.xlsx':
        return remove_metadata_from_xlsx(file_path)

    elif file_extension == '.zip':
        return remove_metadata_from_zip(file_path)

    elif file_extension == '.pptx':
        return remove_metadata_from_pptx(file_path)
    elif file_extension == '.ppt':
        return remove_metadata_from_ppt(file_path)

    elif file_extension == '.odt':
        return remove_metadata_from_odt(file_path)
    elif file_extension == '.ods':
        return remove_metadata_from_ods(file_path)

    elif file_extension == '.epub':
        return remove_metadata_from_epub(file_path)

    elif file_extension == '.rtf':
        return remove_metadata_from_rtf(file_path)

    else:
        logger.warning(f"Unsupported file type {file_extension} for {file_path}.")
        return False
