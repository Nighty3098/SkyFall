import sys
from pathlib import Path

import magic
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser


class MetadataAnalyzer():
    def __init__(self):
        self.result = ""

    def get_file_type(self, path):
        path = Path(path)
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            return f"{file_type}\n"
        except Exception as e:
            return e

    def get_metadata(self, path):
        path = Path(path)
        self.result = ""

        if not path.exists():
            self.result += f"Error: File '{path}' not found."
            return self.result

        self.result += "=" * 50 + "\n"
        self.result += f"File: {path.name}\n"
        self.result += f"Size: {path.stat().st_size / 1024:.2f} KB\n"

        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            self.result += f"MIME type: {file_type}\n"
        except Exception as e:
            self.result += f"Could not determine MIME type: {e}\n"

        self.result += "-" * 50 + "\n"
        self.result += "Metadata:\n"

        parser = createParser(str(path))
        if not parser:
            self.result += "Hachoir could not parse this format.\n"
            return self.result

        try:
            metadata = extractMetadata(parser)
            if metadata:
                text_data = metadata.exportPlaintext()
                for line in text_data:
                    self.result += f"  {line}\n"
            else:
                self.result += "  No metadata found in file.\n"
        except Exception as e:
            self.result += f"Error reading metadata: {e}\n"
        finally:
            parser.stream._input.close()

        self.result += "=" * 50 + "\n"

        return self.result
