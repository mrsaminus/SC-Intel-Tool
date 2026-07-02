from .parser import OCRParser, ParsedOCRResult
from app.hauling import HaulingContractParser


class HaulingContractsOCRParser(OCRParser):
    name = "hauling_contracts"

    def __init__(self, contract_parser=None):
        self.contract_parser = contract_parser or HaulingContractParser()

    def parse(self, result):
        parse_result = self.contract_parser.parse(getattr(result, "text", ""))
        return ParsedOCRResult(
            data=parse_result,
            warnings=parse_result.warnings,
            raw_output=parse_result,
        )
