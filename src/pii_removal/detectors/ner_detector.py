"""
Named Entity Recognition (NER) PII Detector

Uses spaCy NER to detect:
- PERSON entities
- ORG entities
- GPE (geopolitical entities)
- DATE entities

Task Reference: Phase 2, Task 2.3
"""

from typing import List, Dict
import logging

# TODO: Install spaCy and download model
# pip install spacy
# python -m spacy download en_core_web_sm


class NERPIIDetector:
    """Detects PII using spaCy Named Entity Recognition"""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize NER PII Detector

        Args:
            model_name: spaCy model name to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name

        # TODO: Load spaCy model
        # import spacy
        # self.nlp = spacy.load(model_name)

    def detect(self, text: str) -> List[Dict[str, any]]:
        """
        Detect PII using Named Entity Recognition

        Args:
            text: Input text to scan

        Returns:
            List of detected entities
            Example:
            [
                {
                    'type': 'PERSON',
                    'value': 'John Smith',
                    'start': 15,
                    'end': 25
                }
            ]
        """
        if not text:
            return []

        # TODO: Process text with spaCy
        # doc = self.nlp(text)
        # detections = []
        # for ent in doc.ents:
        #     if ent.label_ in ['PERSON', 'ORG', 'GPE', 'DATE']:
        #         detections.append({
        #             'type': ent.label_,
        #             'value': ent.text,
        #             'start': ent.start_char,
        #             'end': ent.end_char
        #         })

        raise NotImplementedError("NER detection not yet implemented")

    def detect_batch(self, texts: List[str]) -> List[List[Dict[str, any]]]:
        """
        Detect PII in batch of texts (optimized for throughput)

        Args:
            texts: List of input texts

        Returns:
            List of detection results for each text
        """
        # TODO: Use spaCy's pipe for efficient batch processing
        # docs = self.nlp.pipe(texts)
        # return [self._extract_entities(doc) for doc in docs]

        raise NotImplementedError("Batch NER detection not yet implemented")

    def _extract_entities(self, doc) -> List[Dict[str, any]]:
        """
        Extract entities from spaCy Doc object

        Args:
            doc: spaCy Doc object

        Returns:
            List of extracted entities
        """
        # TODO: Extract relevant entities
        pass


def main():
    """Test NER detector with sample data"""
    # TODO: Implement test cases
    pass


if __name__ == "__main__":
    main()
