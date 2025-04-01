import argparse
import logging
import os
import csv
from datetime import datetime
from pyzbar.pyzbar import decode
from PIL import Image

class DecodedObjectFile:
    def __init__(self, code, type, filepath):
        self.code = str(code) if code else None
        self.type = type
        self.filepath = filepath

    def is_not_detected(self):
        return self.code is None

class DecodedObjectFileIndex:
    def create_index(dec_objs):
        code2type = {}
        detected = {}
        undetected_objs = []
        for obj in dec_objs:
            if obj.is_not_detected():
                undetected_objs.append(obj.filepath)
                continue

            code2type[obj.code] = obj.type

            if obj.code not in detected:
                detected[obj.code] = []

            detected[obj.code].append(obj.filepath)

        return DecodedObjectFileIndex(detected, undetected_objs, code2type)

    def __init__(self, detected, undetected, code2type):
        self.detected = detected
        self.undetected = undetected
        self._code2type_map = code2type

    def get_decoded_object_type(self, code):
        return self._code2type_map[code]

class DecodedObjectDetector:
    def detect_objects(filepath):
        """Detects a barcode in the given image file and returns the barcode data or None if detection fails."""
        try:
            image = Image.open(filepath)
            objs = decode(image)
            if objs:
                return [DecodedObjectFile(obj.data.decode("utf-8"), obj.type, filepath) for obj in objs]
        except Exception as e:
            logging.error(f"Error detecting barcode in {filepath}: {e}")
        logging.warning("Detected NO barcode in file %s", filepath)
        return [DecodedObjectFile(None, None, filepath)]

class DecodedObjectFolderComparison:
    def __init__(self, obj_index, cmp_dirpaths):
        self.obj_index = obj_index
        self.cmp_dirpaths = cmp_dirpaths
        self.cmp_res = {}

    def compare(self):
        for code, filepaths in self.obj_index.detected.items():
            count_arr = [0 for _ in self.cmp_dirpaths]
            for filepath in filepaths:
                for i, dirpath in enumerate(self.cmp_dirpaths):
                    if filepath.startswith(dirpath + os.sep):
                        count_arr[i] += 1

            self.cmp_res[code] = []

            if all(cnt == 1 for cnt in count_arr):
                self.cmp_res[code].append('MATCH_ALL')
            else:
                if any(cnt == 0 for cnt in count_arr):
                    self.cmp_res[code].append('MISSING')
                if any(cnt > 1 for cnt in count_arr):
                    self.cmp_res[code].append('DUPLICATED')

                if (len(self.cmp_res[code]) == 0):
                    self.cmp_res[code].append('INVALID')
        return self._compare_result()

    def _compare_result(self):
        header = ["Compare Result", "CODE", "Decoded Type", *self.cmp_dirpaths]
        rows = []

        for code, filepaths in self.obj_index.detected.items():
            row = [self.cmp_res[code], code, self.obj_index.get_decoded_object_type(code)]
            for dirpath in self.cmp_dirpaths:
                subpaths = [os.path.relpath(fp, dirpath) for fp in filepaths if fp.startswith(dirpath + os.sep)]
                row.append(subpaths)

            rows.append(row)

        for fp in self.obj_index.undetected:
            row = ["NO_DETECTED", "None", "None"]
            for dirpath in self.cmp_dirpaths:
                row.append(os.path.relpath(fp, dirpath) if fp.startswith(dirpath + os.sep) else "")

            rows.append(row)
        return header, rows

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
            logging.error("Source directory does not exist: %s", path)
            exit(1)

    if not os.path.isdir(report_dirpath):
        logging.error("Report directory does not exist: %s", report_dirpath)
        exit(1)

    dec_objs = []
    for src_dirpath in src_dirpaths:
        for dirpath, _, filenames in os.walk(src_dirpath):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                dec_objs_in_file = DecodedObjectDetector.detect_objects(filepath)
                dec_objs.extend(dec_objs_in_file)

    obj_index = DecodedObjectFileIndex.create_index(dec_objs)

    obj_compare = DecodedObjectFolderComparison(obj_index, src_dirpaths)
    header, rows = obj_compare.compare()

    with open(report_filepath, mode="w", newline="") as file:
        def format_csv_record(val):
            if isinstance(val, (list, tuple)):
                return '\n'.join(val)
            else:
                return val

        writer = csv.writer(file)
        writer.writerow(header)
        for row in rows:
            fmt_row = [format_csv_record(val) for val in row]
            writer.writerow(fmt_row)

if __name__ == "__main__":
    main()
