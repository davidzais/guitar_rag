from functools import cache
from llm import get_llm
from typing import cast
from models.classification import Classification
from classification.policy import should_keep
from db.db_service import get_scraped, mark_classified
from db.database import Status
import structlog

logger = structlog.get_logger()



def build_input(title: str, full_text: str, sample_chars_size: int = 1500) -> str:  
    sample = full_text[0: sample_chars_size]

    return f"Title: {title} Transcript sample: {sample}"

def classify(title: str, text: str) -> Classification:
    prompt = build_classification_prompt(build_input(title, text))
    return cast( Classification, get_classifier().invoke(prompt)) # returns a validated Classification instance)




def build_classification_prompt(input_text: str) -> str:
    return f"""You are classifying a YouTube guitar video into exactly one category, \
based on its title and a sample of its transcript.

We are building a guitar-instruction knowledge base. We only want videos that TEACH \
generalizable technique, theory, or musical concepts. Classify into one category:

- INSTRUCTION: Teaches technique, theory, or a concept that transfers to other songs and \
contexts (e.g. "how to use the mixolydian mode", "alternate picking exercises", \
"3 ways to spice up your blues licks"). This is the only category we keep.

- SONG_TUTORIAL: Teaches how to play one specific, named song or piece (e.g. \
"how to play Stairway to Heaven"). Even though it instructs, the knowledge is tied to \
that one song, so it does NOT count as INSTRUCTION.

- PERFORMANCE: The instructor mostly plays — a full song, an improvisation, a live clip — \
with little or no teaching.

- PRODUCT_DEMO: A gear review, demo, or comparison (guitars, pedals, amps, software).

- OTHER: Anything else — vlog, channel update, Q&A, intro, announcement.

Guidance:
- Base your decision only on the title and transcript sample provided.
- The key distinction is INSTRUCTION (generalizable) vs SONG_TUTORIAL (one specific song). \
When a video teaches, ask: would this knowledge help with songs other than the one shown? \
If yes, INSTRUCTION; if it only helps with that one named song, SONG_TUTORIAL.
- Set confidence honestly. If the sample is short or ambiguous, lower your confidence \
rather than guessing high.
- Give a brief reason (one sentence) for your choice.

{input_text}
"""

@cache
def get_classifier():
    llm = get_llm()
    return llm.with_structured_output( Classification)


def run_classify():
    rows= get_scraped()
    
    logger.info(f"classifier got {len(rows)} transcripts to classify...")
    for row in rows:
        try:
            title = row.title
            text = row.payload["text"]

            result = classify(title, text)
           
            if should_keep(result):
                status = Status.CLASSIFIED_KEEP
                reason = None
            else:
                status = Status.CLASSIFIED_REJECT
                reason = result.reason

            mark_classified(row.video_id, status, reason)
            logger.info("classified", video_id=row.video_id,
                        category=result.category.value, confidence=result.confidence,
                        kept=should_keep(result), reason=result.reason)

        except Exception:            
            logger.error(f"Error classifying video_id: {row.video_id}", exc_info=True )
        
    

if __name__ == "__main__":
    run_classify()