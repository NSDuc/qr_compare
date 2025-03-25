# QR Code Detector

This Python script detects QR codes from MULTIPLE FOLDER and compare them.

## Installation

### 1. Clone the Repository (if applicable)
```sh
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Install Dependencies
```sh
pip install -r requirements.txt
```

### 3. Usage


```sh
# use absolulate path
python main.py --src-dir=..\barcode_compare\images\QR01 --src-dir=D:\projects\barcode_compare\images\QR02 --src-dir=images\All_QR
# use relative path
python main.py --src-dir=images\QR01 --src-dir=images\QR02 --src-dir=images\All_QR --log-level=DEBUG
```
