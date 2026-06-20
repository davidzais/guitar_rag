from models.classification import Classification, Category


MIN_CONFIDENCE = 0.7


def should_keep(result: Classification) -> bool:
    return result.category == Category.INSTRUCTION and result.confidence >= MIN_CONFIDENCE