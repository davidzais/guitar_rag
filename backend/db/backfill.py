
from ingestion.ingest import load_data_filelist, load_transcript
from models.transcript import Transcript
from db.db_service import add_transcripts


def get_all_transcripts() -> list[Transcript]:
    file_list = load_data_filelist()
    all_transcripts: list[Transcript] = []
    for path in file_list:
        transcript = load_transcript(path)
        if transcript:
            all_transcripts.append( transcript)
       
    return all_transcripts


def main() -> None:
    transcripts = get_all_transcripts()
    add_transcripts( transcripts)

    

if __name__ == "__main__":
    main()