import argparse
import logging
import os
import csv
from datetime import datetime
from pyzbar.pyzbar import decode
from PIL import Image

class QRCodeFile:
    def __init__(self, code, filepath):
        self.code = str(code) if code is not None else None
        self.filepath = filepath

    def is_not_detected(self):
        return self.code is None

class QRCodeFileIndex:
    def create_from_qrcodes(qrcodes):
        detected = {}
        undetected = []
        for qrcode in qrcodes:
            if qrcode.is_not_detected():
                undetected.append(qrcode.filepath)
                continue
            
            if qrcode.code not in detected:
                detected[qrcode.code] = []

            detected[qrcode.code].append(qrcode.filepath)

        return QRCodeFileIndex(detected, undetected)

    def __init__(self, detected, undetected):
        self.detected = detected
        self.undetected = undetected

class QRCodeDetector:
    def detect_qrcode_id(filepath):
        """Detects a barcode in the given image file and returns the barcode data or None if detection fails."""
        try:
            image = Image.open(filepath)
            qrs = decode(image)
            if qrs:
                return [qr.data.decode("utf-8") for qr in qrs]
        except Exception as e:
            logging.error(f"Error detecting barcode in {filepath}: {e}")
        logging.warning("Detected NO barcode in file %s", filepath)
        return [None]

    def detect_qrcode_image(filepath):
        qrcode_ids = QRCodeDetector.detect_qrcode_id(filepath)
        return [QRCodeFile(qrcode_id, filepath) for qrcode_id in qrcode_ids]

class QRCodeFolderComparison:
    def __init__(self, qrindex, compare_dirpaths):
        self.qrindex = qrindex
        self.compare_dirpaths = compare_dirpaths
        self.compare_result = {}

    def compare(self):
        for code, filepaths in self.qrindex.detected.items():
            srccnts = [0 for _ in self.compare_dirpaths]
            for filepath in filepaths:
                for i, dirpath in enumerate(self.compare_dirpaths):
                    if filepath.startswith(dirpath + os.sep):
                        srccnts[i] += 1

            if all(cnt == 1 for cnt in srccnts):
                self.compare_result[code] = 'MATCHED'
            elif any(cnt == 0 for cnt in srccnts):
                self.compare_result[code] = 'MISSING'
            elif any(cnt > 1 for cnt in srccnts):
                self.compare_result[code] = 'DUPLICATED'
            else:
                self.compare_result[code] = 'INVALID'

    def export_to_csv(self, report_filepath):
        def format_cell_subpaths(subpaths):
            return '\n'.join(subpaths)

        with open(report_filepath, mode="w", newline="") as file:
            writer = csv.writer(file)
            header = ["Compare Result", "QR Code", *self.compare_dirpaths]
            writer.writerow(header)

            for code, filepaths in self.qrindex.detected.items():
                row = [self.compare_result[code], code]
                for dirpath in self.compare_dirpaths:
                    subpaths = [os.path.relpath(fp, dirpath) for fp in filepaths if fp.startswith(dirpath + os.sep)]
                    row.append(format_cell_subpaths(subpaths))

                writer.writerow(row)

            for fp in self.qrindex.undetected:
                row = ["UN_DETECTED", ""]
                for dirpath in self.compare_dirpaths:
                    row.append(os.path.relpath(fp, dirpath) if fp.startswith(dirpath + os.sep) else "")

                writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Process command-line arguments.")
    parser.add_argument("--src-dir", action="append", required=True, help="Source directory path (must be used at least once)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set logging level (default: INFO)")
    parser.add_argument("--report-dir", default=os.getcwd(), help="Report directory path (default: current working directory)")

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format='%(levelname)s: %(message)s')

    src_dirpaths = [os.path.abspath(src) for src in args.src_dir]
    report_dirpath = os.path.abspath(args.report_dir)
    report_filename = datetime.now().strftime("qr_comparison_report_%Y-%m-%d_%H-%M-%S.csv")
    report_filepath = os.path.join(report_dirpath, report_filename)

    for path in src_dirpaths:
        if not os.path.isdir(path):
            logging.error("Invalid source directory: %s", path)
            exit(1)

    if not os.path.isdir(report_dirpath):
        logging.error("Report directory does not exist: %s", report_dirpath)
        exit(1)

    qrcodes = []
    for src_dirpath in src_dirpaths:
        for dirpath, _, filenames in os.walk(src_dirpath):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                qrcodes_in_file= QRCodeDetector.detect_qrcode_image(filepath)

                qrcodes.extend(qrcodes_in_file)

    qrindex = QRCodeFileIndex.create_from_qrcodes(qrcodes)

    qrcompare = QRCodeFolderComparison(qrindex, src_dirpaths)
    qrcompare.compare()
    qrcompare.export_to_csv(report_filepath)
    logging.info("[Exported]: %s", report_filepath)


if __name__ == "__main__":
    main()
