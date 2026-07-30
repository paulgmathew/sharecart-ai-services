from enum import Enum


class ScanType(str, Enum):
    RECEIPT = "RECEIPT"
    PRICE_TAG = "PRICE_TAG"
