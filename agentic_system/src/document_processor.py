import os
from typing import Dict, Optional
import PyPDF2
from docx import Document
from odf import text as odf_text, teletype
from odf.opendocument import load as odf_load
from PIL import Image
import pytesseract

class DocumentProcessor:
    """
    Processes various document formats (PDF, DOCX, ODT) and extracts text content.
    """
    
    def __init__(self):
        """initialize document processor."""
        self.supported_formats = {
            'pdf': self.extract_text_from_pdf,
            'docx': self.extract_text_from_docx,
            'odt': self.extract_text_from_odt,
            'png': self.extract_text_from_image,
            'jpg': self.extract_text_from_image,
            'jpeg': self.extract_text_from_image
        }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file.
        
        Args:
            file_path (str): path to PDF file
            
        Returns:
            str: extracted text
        """
        try:
            text = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return '\n\n'.join(text)
        except Exception as e:
            print(f"error extracting pdf: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX file.
        
        Args:
            file_path (str): path to DOCX file
            
        Returns:
            str: extracted text
        """
        try:
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text.append(paragraph.text)
            return '\n\n'.join(text)
        except Exception as e:
            print(f"error extracting docx: {e}")
            return ""
    
    def extract_text_from_odt(self, file_path: str) -> str:
        """
        Extract text from ODT file.
        
        Args:
            file_path (str): path to ODT file
            
        Returns:
            str: extracted text
        """
        try:
            doc = odf_load(file_path)
            text = []
            for item in doc.getElementsByType(odf_text.P):
                paragraph_text = teletype.extractText(item)
                if paragraph_text.strip():
                    text.append(paragraph_text)
            return '\n\n'.join(text)
        except Exception as e:
            print(f"error extracting odt: {e}")
            return ""
    
    def extract_text_from_image(self, file_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            file_path (str): path to image file
            
        Returns:
            str: extracted text
        """
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"error extracting text from image: {e}")
            return ""
    
    def process_file(self, file_path: str) -> Dict[str, str]:
        """
        Process file and extract text based on extension.
        
        Args:
            file_path (str): path to file
            
        Returns:
            Dict: contains 'text' and 'type' of document
        """
        ext = os.path.splitext(file_path)[1][1:].lower()
        
        if ext not in self.supported_formats:
            return {
                "error": f"unsupported file format: {ext}",
                "supported": list(self.supported_formats.keys())
            }
        
        text = self.supported_formats[ext](file_path)
        
        return {
            "text": text,
            "type": ext,
            "length": len(text),
            "path": file_path
        }
