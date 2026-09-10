import asyncio
import io
import struct
from pathlib import Path

import numpy as np
from loguru import logger
from PIL import Image, ImageChops, ImageEnhance

from src.ui.output_formatter import (
    divider,
    end_of,
    error,
    info,
    kv,
    line,
    section,
    title,
)

PNG_IEND = b"IEND\xaeB`\x82"
JPEG_EOI = b"\xff\xd9"
GIF_TRAILER = b"\x3b"
BMP_END_OFFSET = 2  # BMP files have no end marker, just fixed header


def _is_image(path: str) -> bool:
    ext = Path(path).suffix.lower()
    return ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"}


class SteganographyAnalyzer:
    def __init__(self):
        logger.debug("Init: SteganographyAnalyzer")

    async def _read_file_bytes(self, path: str) -> bytes:
        def _read():
            with open(path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def analyze_lsb(self, path: str) -> str:
        result = divider() + "\n"
        result += title("LSB Steganography Analysis") + "\n"

        if not _is_image(path):
            result += error("File is not a supported image format.") + "\n"
            result += info("Supported: PNG, JPEG, GIF, BMP, TIFF, WebP") + "\n"
            result += end_of("lsb analysis") + "\n"
            result += divider() + "\n"
            return result

        try:

            def _lsb_analysis(p):
                img = Image.open(p)
                if img.mode == "P":
                    img = img.convert("RGB")
                elif img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                pixels = np.array(img, dtype=np.uint8)
                channels = ["R", "G", "B"]
                if img.mode == "RGBA":
                    channels.append("A")

                report = ""
                for i, name in enumerate(channels):
                    channel = pixels[:, :, i]
                    lsb_plane = channel & 1
                    ones = int(np.sum(lsb_plane))
                    total = lsb_plane.size
                    ratio = ones / total if total > 0 else 0

                    report += line(f"Channel {name}:") + "\n"
                    report += kv("  Pixels", total) + "\n"
                    report += kv("  LSB=1 count", ones) + "\n"
                    report += kv("  LSB=0 count", total - ones) + "\n"
                    report += kv("  Ratio (1s/total)", f"{ratio:.6f}") + "\n"

                    if 0.48 < ratio < 0.52:
                        report += kv("  Verdict", "Balanced (normal)") + "\n"
                    elif ratio > 0.55 or ratio < 0.45:
                        report += (
                            kv("  Verdict", "SKEWED - possible LSB embedding") + "\n"
                        )
                    else:
                        report += kv("  Verdict", "Slightly uneven") + "\n"

                chi_r = _chi_squared_test(pixels[:, :, 0] & 1)
                chi_g = _chi_squared_test(pixels[:, :, 1] & 1)
                chi_b = _chi_squared_test(pixels[:, :, 2] & 1)
                report += "\n"
                report += line("Chi-squared test on LSB plane:") + "\n"
                report += kv("  R chi2", f"{chi_r:.4f}") + "\n"
                report += kv("  G chi2", f"{chi_g:.4f}") + "\n"
                report += kv("  B chi2", f"{chi_b:.4f}") + "\n"
                if chi_r < 1.0 and chi_g < 1.0 and chi_b < 1.0:
                    report += (
                        kv(
                            "  Verdict",
                            "Low chi2 - LSBs look uniform (possible stego)",
                        )
                        + "\n"
                    )
                elif chi_r > 3.84 or chi_g > 3.84 or chi_b > 3.84:
                    report += (
                        kv("  Verdict", "High chi2 - LSBs are noisy (normal)") + "\n"
                    )

                if img.mode == "RGBA":
                    alpha = pixels[:, :, 3]
                    unique_alpha = len(np.unique(alpha))
                    report += "\n"
                    report += line("Alpha channel check:") + "\n"
                    report += kv("  Unique alpha values", unique_alpha) + "\n"
                    if unique_alpha == 1:
                        report += (
                            kv(
                                "  Note",
                                "Uniform alpha - no hidden data in alpha channel",
                            )
                            + "\n"
                        )
                    elif unique_alpha > 2:
                        report += (
                            kv(
                                "  Note",
                                "Non-uniform alpha - check for hidden data",
                            )
                            + "\n"
                        )

                size_kb = img.size[0] * img.size[1] * len(channels) / 1024
                report += "\n"
                report += kv("Image dimensions", f"{img.size[0]}x{img.size[1]}") + "\n"
                report += kv("Mode", img.mode) + "\n"
                report += kv("Pixel data size", f"{size_kb:.1f} KB") + "\n"

                max_bits = img.size[0] * img.size[1] * len(channels)
                max_bytes = max_bits // 8
                report += kv("Max hidden data (all LSBs)", f"{max_bytes} bytes") + "\n"
                report += (
                    kv(
                        "Max hidden data (2 LSBs/px)",
                        f"{max_bytes * 2} bytes",
                    )
                    + "\n"
                )

                return report

            return await asyncio.to_thread(_lsb_analysis, path)

        except Exception as e:
            result += error(f"LSB analysis failed: {e}") + "\n"

        result += end_of("lsb analysis") + "\n"
        result += divider() + "\n"
        return result

    async def analyze_spectral(self, path: str) -> str:
        result = divider() + "\n"
        result += title("Spectral Analysis") + "\n"

        if not _is_image(path):
            result += error("File is not a supported image format.") + "\n"
            result += info("Supported: PNG, JPEG, GIF, BMP, TIFF, WebP") + "\n"
            result += end_of("spectral analysis") + "\n"
            result += divider() + "\n"
            return result

        try:

            def _spectral(p):
                img = Image.open(p)
                if img.mode == "P":
                    img = img.convert("L")
                elif img.mode != "L":
                    img = img.convert("L")
                pixels = np.array(img, dtype=np.float64)

                report = ""
                report += kv("Image dimensions", f"{img.size[0]}x{img.size[1]}") + "\n"

                f_transform = np.fft.fft2(pixels)
                f_shifted = np.fft.fftshift(f_transform)
                magnitude = np.abs(f_shifted)
                magnitude_log = np.log1p(magnitude)

                report += "\n"
                report += line("FFT Magnitude Statistics:") + "\n"
                report += kv("  Mean", f"{magnitude.mean():.2f}") + "\n"
                report += kv("  Std Dev", f"{magnitude.std():.2f}") + "\n"
                report += kv("  Max", f"{magnitude.max():.2f}") + "\n"
                report += kv("  Min", f"{magnitude.min():.2f}") + "\n"

                h, w = pixels.shape
                cy, cx = h // 2, w // 2
                low = magnitude_log[
                    cy - h // 8 : cy + h // 8, cx - w // 8 : cx + w // 8
                ]
                high = magnitude_log.copy()
                high[cy - h // 8 : cy + h // 8, cx - w // 8 : cx + w // 8] = 0

                report += "\n"
                report += line("Frequency Band Energy:") + "\n"
                report += kv("  Low-freq energy (center)", f"{low.mean():.2f}") + "\n"
                high_nonzero = high[high > 0]
                if high_nonzero.size > 0:
                    high_energy = float(high_nonzero.mean())
                else:
                    high_energy = 0.0
                report += kv("  High-freq energy (outer)", f"{high_energy:.2f}") + "\n"

                hf_ratio = high_energy / low.mean() if low.mean() > 0 else 0
                report += kv("  HF/LF ratio", f"{hf_ratio:.4f}") + "\n"

                report += "\n"
                report += line("Anomaly Detection:") + "\n"

                mid_freq = magnitude_log.copy()
                r = min(h, w) // 16
                y, x = np.ogrid[:h, :w]
                mask_circle = ((y - cy) ** 2 + (x - cx) ** 2) > r**2
                mask_inner = ((y - cy) ** 2 + (x - cx) ** 2) < (min(h, w) // 3) ** 2
                mid_freq[mask_circle] = 0
                mid_freq[~mask_inner] = 0

                if mid_freq.size > 0 and mid_freq.max() > 0:
                    mid_std = mid_freq[mid_freq > 0].std()
                    report += kv("  Mid-freq band std", f"{mid_std:.4f}") + "\n"
                else:
                    mid_std = 0
                    report += kv("  Mid-freq band std", "N/A") + "\n"

                for angle_step in [0, 45, 90, 135]:
                    if angle_step == 0:
                        diag = np.diag(magnitude_log, k=0)
                    elif angle_step == 45:
                        diag = np.diag(magnitude_log, k=h // 8)
                    elif angle_step == 90:
                        diag = np.diag(magnitude_log.T, k=0)
                    else:
                        diag = np.diag(magnitude_log, k=-h // 8)
                    if len(diag) > 0:
                        diag_std = float(np.std(diag))
                    else:
                        diag_std = 0
                    report += (
                        kv(f"  Diagonal @{angle_step} deg std", f"{diag_std:.4f}")
                        + "\n"
                    )

                suspicious = 0
                notes = []
                if hf_ratio > 0.7:
                    suspicious += 1
                    notes.append("Unusually high HF energy")
                if mid_std > 1.5:
                    suspicious += 1
                    notes.append("Mid-freq band has anomalies")

                report += "\n"
                if suspicious > 0:
                    report += kv("Overall", f"{suspicious} anomalies detected") + "\n"
                    for n in notes:
                        report += line(f"  - {n}") + "\n"
                else:
                    report += kv("Overall", "No significant spectral anomalies") + "\n"

                return report

            return await asyncio.to_thread(_spectral, path)

        except Exception as e:
            result += error(f"Spectral analysis failed: {e}") + "\n"

        result += end_of("spectral analysis") + "\n"
        result += divider() + "\n"
        return result

    async def analyze_eoi(self, path: str) -> str:
        result = divider() + "\n"
        result += title("EOI/EOD Marker Analysis") + "\n"

        data = await self._read_file_bytes(path)
        ext = Path(path).suffix.lower()
        file_size = len(data)

        result += kv("File size", f"{file_size} bytes") + "\n"
        result += kv("File extension", ext) + "\n"

        if ext == ".png":
            result += self._analyze_png_eoi(data)
        elif ext in (".jpg", ".jpeg"):
            result += self._analyze_jpeg_eoi(data)
        elif ext == ".gif":
            result += self._analyze_gif_eoi(data)
        elif ext == ".bmp":
            result += self._analyze_bmp_eoi(data)
        elif ext in (".tiff", ".tif"):
            result += self._analyze_tiff_eoi(data)
        elif ext == ".webp":
            result += self._analyze_webp_eoi(data)
        else:
            result += info("Generic binary analysis (unknown format)") + "\n"
            result += self._analyze_generic_eoi(data)

        result += end_of("eoi/eod analysis") + "\n"
        result += divider() + "\n"
        return result

    def _analyze_png_eoi(self, data: bytes) -> str:
        result = ""
        result += section("PNG IEND Chunk Analysis") + "\n"

        iend_positions = []
        start = 0
        while True:
            idx = data.find(PNG_IEND, start)
            if idx == -1:
                break
            iend_positions.append(idx)
            start = idx + len(PNG_IEND)

        if not iend_positions:
            result += error("No IEND chunk found! Corrupted PNG.") + "\n"
            return result

        result += kv("IEND markers found", len(iend_positions)) + "\n"
        for i, pos in enumerate(iend_positions):
            result += kv(f"  IEND #{i + 1} offset", f"0x{pos:08X} ({pos})") + "\n"

        last_iend = iend_positions[-1] + len(PNG_IEND)
        tail = data[last_iend:]

        if len(tail) > 0:
            result += (
                info(
                    f"Hidden data after IEND! "
                    f"{len(tail)} bytes at offset 0x{last_iend:08X}"
                )
                + "\n"
            )
            result += self._hex_dump(tail[:128], last_iend)
            if len(tail) > 128:
                result += line(f"  ... ({len(tail) - 128} more bytes)") + "\n"
            result += self._identify_tail_content(tail)
        else:
            result += info("No data after IEND - file is clean.") + "\n"

        if len(iend_positions) > 1:
            result += (
                info(
                    f"WARNING: Multiple IEND markers "
                    f"({len(iend_positions)}) - suspicious!"
                )
                + "\n"
            )

        return result

    def _analyze_jpeg_eoi(self, data: bytes) -> str:
        result = ""
        result += section("JPEG EOI Marker Analysis") + "\n"

        eoi_positions = []
        start = 0
        while True:
            idx = data.find(JPEG_EOI, start)
            if idx == -1:
                break
            eoi_positions.append(idx)
            start = idx + 2

        if not eoi_positions:
            result += error("No EOI marker (FFD9) found! Corrupted JPEG.") + "\n"
            return result

        result += kv("EOI markers found", len(eoi_positions)) + "\n"
        for i, pos in enumerate(eoi_positions):
            result += kv(f"  EOI #{i + 1} offset", f"0x{pos:08X} ({pos})") + "\n"

        last_eoi = eoi_positions[-1] + 2
        tail = data[last_eoi:]

        if len(tail) > 0:
            result += (
                info(
                    f"Hidden data after EOI! "
                    f"{len(tail)} bytes at offset 0x{last_eoi:08X}"
                )
                + "\n"
            )
            result += self._hex_dump(tail[:128], last_eoi)
            if len(tail) > 128:
                result += line(f"  ... ({len(tail) - 128} more bytes)") + "\n"
            result += self._identify_tail_content(tail)
        else:
            result += info("No data after EOI - file is clean.") + "\n"

        if len(eoi_positions) > 1:
            result += (
                info(
                    f"WARNING: Multiple EOI markers "
                    f"({len(eoi_positions)}) - suspicious!"
                )
                + "\n"
            )

        return result

    def _analyze_gif_eoi(self, data: bytes) -> str:
        result = ""
        result += section("GIF Trailer Analysis") + "\n"

        trailer_pos = data.rfind(GIF_TRAILER)
        if trailer_pos == -1:
            result += error("No GIF trailer (0x00) found.") + "\n"
            return result

        result += (
            kv(
                "GIF trailer offset",
                f"0x{trailer_pos:08X} ({trailer_pos})",
            )
            + "\n"
        )
        tail = data[trailer_pos + 1 :]

        if len(tail) > 0:
            result += (
                info(
                    f"Hidden data after GIF trailer! "
                    f"{len(tail)} bytes at offset "
                    f"0x{trailer_pos + 1:08X}"
                )
                + "\n"
            )
            result += self._hex_dump(tail[:128], trailer_pos + 1)
            if len(tail) > 128:
                result += line(f"  ... ({len(tail) - 128} more bytes)") + "\n"
            result += self._identify_tail_content(tail)
        else:
            result += info("No data after GIF trailer - file is clean.") + "\n"

        return result

    def _analyze_bmp_eoi(self, data: bytes) -> str:
        result = ""
        result += section("BMP Structure Analysis") + "\n"

        if len(data) < 2:
            result += error("File too small to be a valid BMP.") + "\n"
            return result

        if data[:2] != b"BM":
            result += error("Not a valid BMP file (missing BM header).") + "\n"
            return result

        pixel_offset = struct.unpack_from("<I", data, 10)[0]
        result += (
            kv(
                "Pixel data offset",
                f"0x{pixel_offset:08X} ({pixel_offset})",
            )
            + "\n"
        )

        header_size = pixel_offset
        result += kv("Header size", f"{header_size} bytes") + "\n"

        if len(data) > pixel_offset + 1024:
            result += info("BMP has no explicit end marker.") + "\n"
            result += info("Check file size against expected dimensions.") + "\n"
        else:
            result += info("File size appears consistent with header.") + "\n"

        return result

    def _analyze_tiff_eoi(self, data: bytes) -> str:
        result = ""
        result += section("TIFF Structure Analysis") + "\n"

        if data[:2] in (b"II", b"MM"):
            byte_order = "Little-endian" if data[:2] == b"II" else "Big-endian"
            result += kv("Byte order", byte_order) + "\n"
            result += info("TIFF has no explicit end marker.") + "\n"
            result += (
                info("File size and IFD entries should be checked manually.") + "\n"
            )
        else:
            result += error("Not a valid TIFF file.") + "\n"

        return result

    def _analyze_webp_eoi(self, data: bytes) -> str:
        result = ""
        result += section("WebP Container Analysis") + "\n"

        if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            result += error("Not a valid WebP file.") + "\n"
            return result

        riff_size = struct.unpack_from("<I", data, 4)[0]
        result += kv("RIFF declared size", f"{riff_size} bytes") + "\n"
        result += kv("Actual file size", f"{len(data)} bytes") + "\n"

        expected = riff_size + 8
        if len(data) > expected:
            tail_len = len(data) - expected
            result += (
                info(
                    f"Hidden data after RIFF container! "
                    f"{tail_len} bytes at offset "
                    f"0x{expected:08X}"
                )
                + "\n"
            )
            result += self._hex_dump(data[expected : expected + 128], expected)
            result += self._identify_tail_content(data[expected:])
        elif len(data) < expected:
            result += (
                error("File is truncated (less data than RIFF header declares).") + "\n"
            )
        else:
            result += info("No extra data after RIFF container - file is clean.") + "\n"

        return result

    def _analyze_generic_eoi(self, data: bytes) -> str:
        result = ""
        result += section("Generic End-of-File Analysis") + "\n"

        i = len(data) - 1
        while i >= 0 and data[i] == 0x00:
            i -= 1
        null_tail = len(data) - 1 - i
        if null_tail > 16:
            result += kv("Null byte padding at end", f"{null_tail} bytes") + "\n"
            result += info("Possible padding or hidden null data.") + "\n"

        if null_tail > 16:
            after_last_content = i + 1
            result += (
                kv(
                    "Last non-null byte offset",
                    f"0x{i:08X}",
                )
                + "\n"
            )
            result += (
                kv(
                    "Data after last content",
                    f"{len(data) - after_last_content} bytes",
                )
                + "\n"
            )

        return result

    async def detect_tail_data(self, path: str) -> str:
        data = await self._read_file_bytes(path)

        result = divider() + "\n"
        result += title("Tail Data Detection") + "\n"
        result += kv("File size", f"{len(data)} bytes") + "\n"

        hidden_sections = []

        idx = data.find(PNG_IEND)
        if idx != -1:
            tail_start = idx + len(PNG_IEND)
            tail = data[tail_start:]
            if len(tail) > 0:
                hidden_sections.append(("PNG IEND", tail_start, tail))

        for marker_name, marker in [
            ("JPEG EOI", JPEG_EOI),
            ("GIF Trailer", GIF_TRAILER),
        ]:
            idx = data.find(marker)
            if idx != -1:
                if marker_name == "GIF Trailer":
                    tail_start = idx + 1
                else:
                    tail_start = idx + 2
                tail = data[tail_start:]
                if len(tail) > 0:
                    hidden_sections.append((marker_name, tail_start, tail))

        if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
            riff_size = struct.unpack_from("<I", data, 4)[0] + 8
            if len(data) > riff_size:
                tail = data[riff_size:]
                hidden_sections.append(("WebP RIFF", riff_size, tail))

        if hidden_sections:
            for name, offset, tail in hidden_sections:
                result += (
                    info(
                        f"Hidden data found after {name}! "
                        f"Offset: 0x{offset:08X}, Size: {len(tail)} bytes"
                    )
                    + "\n"
                )
                result += self._hex_dump(tail[:64], offset)
                if len(tail) > 64:
                    result += line(f"  ... ({len(tail) - 64} more bytes)") + "\n"
                result += self._identify_tail_content(tail) + "\n"
        else:
            result += info("No hidden tail data detected in known formats.") + "\n"

        result += end_of("tail data detection") + "\n"
        result += divider() + "\n"
        return result

    async def run_full_analysis(self, path: str) -> dict:
        results = {}
        results["lsb"] = await self.analyze_lsb(path)
        results["spectral"] = await self.analyze_spectral(path)
        results["eoi"] = await self.analyze_eoi(path)
        results["tail"] = await self.detect_tail_data(path)
        results["ela"] = await self.analyze_ela(path)
        return results

    async def analyze_ela(self, path: str, quality: int = 90) -> str:
        result = divider() + "\n"
        result += title("ELA (Error Level Analysis)") + "\n"

        if not _is_image(path):
            result += error("File is not a supported image format.") + "\n"
            result += info("Supported: PNG, JPEG, GIF, BMP, TIFF, WebP") + "\n"
            result += end_of("ela analysis") + "\n"
            result += divider() + "\n"
            return result

        try:

            def _ela(p, q):
                orig = Image.open(p).convert("RGB")
                buf = io.BytesIO()
                orig.save(buf, format="JPEG", quality=q)
                buf.seek(0)
                resaved = Image.open(buf).convert("RGB")

                diff = ImageChops.difference(orig, resaved)
                extrema = diff.getextrema()
                max_diff = max(e[1] for e in extrema)

                # Amplify for heatmap: scale so max difference maps to 255
                scale = 255.0 / max_diff if max_diff > 0 else 1.0
                heatmap = ImageEnhance.Brightness(diff).enhance(scale)

                arr = np.array(diff.convert("L"), dtype=np.float64)
                mean = float(arr.mean())
                std = float(arr.std())
                p95 = float(np.percentile(arr, 95))
                hot_ratio = float(np.mean(arr > 30))

                # JPEG block-level check: 8x8 grid means, hot blocks share
                h, w = arr.shape
                bh, bw = h // 8, w // 8
                hot_blocks = 0
                total_blocks = 0
                block_std = 0.0
                if bh > 0 and bw > 0:
                    trimmed = arr[: bh * 8, : bw * 8]
                    blocks = trimmed.reshape(bh, 8, bw, 8).mean(axis=(1, 3))
                    block_means = blocks.flatten()
                    total_blocks = int(blocks.size)
                    hot_blocks = int(np.sum(blocks > 30))
                    block_std = float(np.std(block_means))

                heatmap_path = str(Path(p).with_name(Path(p).stem + "_ela.png"))
                heatmap.save(heatmap_path)

                report = ""
                report += (
                    kv("Image dimensions", f"{orig.size[0]}x{orig.size[1]}") + "\n"
                )
                report += kv("Recompress quality", f"JPEG Q={q}") + "\n"
                report += kv("Max channel diff", max_diff) + "\n"
                report += kv("Mean diff (grayscale)", f"{mean:.2f}") + "\n"
                report += kv("Std dev", f"{std:.2f}") + "\n"
                report += kv("95th percentile", f"{p95:.2f}") + "\n"
                report += kv("Hot pixels (>30)", f"{hot_ratio * 100:.2f}%") + "\n"
                if total_blocks:
                    report += (
                        kv("Hot 8x8 blocks (>30)", f"{hot_blocks}/{total_blocks}")
                        + "\n"
                    )
                    report += kv("Block means std", f"{block_std:.2f}") + "\n"
                report += kv("Heatmap saved", heatmap_path) + "\n"
                report += "\n"

                hot_block_frac = hot_blocks / total_blocks if total_blocks else 0.0
                if max_diff == 0:
                    report += kv("Verdict", "Zero ELA response - uniform image") + "\n"
                elif mean > 12 or hot_ratio > 0.25:
                    report += (
                        kv(
                            "Verdict",
                            "High overall ELA - resaved/low-quality, inconclusive",
                        )
                        + "\n"
                    )
                elif hot_block_frac > 0.005 or (block_std > 8 and hot_ratio > 0.005):
                    report += (
                        kv(
                            "Verdict",
                            "LOCALIZED bright regions - possible edit/paste",
                        )
                        + "\n"
                    )
                else:
                    report += (
                        kv("Verdict", "Uniform ELA - no obvious local edits") + "\n"
                    )
                return report

            result += await asyncio.to_thread(_ela, path, quality)

        except Exception as e:
            result += error(f"ELA analysis failed: {e}") + "\n"

        result += end_of("ela analysis") + "\n"
        result += divider() + "\n"
        return result

    def _hex_dump(self, data: bytes, base_offset: int = 0) -> str:
        result = ""
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            result += (
                line(f"  {base_offset + i:08X}  {hex_part:<48s}  {ascii_part}") + "\n"
            )
        return result

    def _identify_tail_content(self, data: bytes) -> str:
        result = ""
        if len(data) == 0:
            return result

        signatures = {
            b"\x89PNG": "PNG image",
            b"\xff\xd8\xff": "JPEG image",
            b"GIF87a": "GIF87a image",
            b"GIF89a": "GIF89a image",
            b"PK": "ZIP archive / PKZIP",
            b"\x1f\x8b": "GZIP compressed data",
            b"Rar!": "RAR archive",
            b"\x7fELF": "ELF executable",
            b"MZ": "PE/EXE executable",
            b"%PDF": "PDF document",
            b"\x50\x4b\x03\x04": "ZIP archive",
            b"SQLite format 3": "SQLite database",
            b"\x00\x00\x00": "Binary data (null bytes)",
            b"http": "HTTP URL or data",
            b"<!DOCTYPE": "HTML document",
            b"<html": "HTML document",
        }

        for sig, desc in signatures.items():
            if data[: len(sig)] == sig:
                result += line(f"  Detected content type: {desc}") + "\n"
                return result

        printable_count = sum(1 for b in data[:64] if 32 <= b < 127 or b in (9, 10, 13))
        ratio = printable_count / min(64, len(data))
        if ratio > 0.8:
            result += line("  Detected content type: Likely text/ASCII data") + "\n"
            try:
                preview = data[:200].decode("ascii", errors="replace")
                result += line(f"  Preview: {preview[:100]}") + "\n"
            except Exception:
                pass
        else:
            result += line("  Detected content type: Binary data") + "\n"

        return result


def _chi_squared_test(lsb_plane: np.ndarray) -> float:
    flat = lsb_plane.flatten().astype(np.float64)
    n = flat.size
    if n == 0:
        return 0.0
    observed_ones = float(np.sum(flat))
    observed_zeros = n - observed_ones
    expected = n / 2.0
    chi2 = ((observed_ones - expected) ** 2) / expected + (
        (observed_zeros - expected) ** 2
    ) / expected
    return chi2
