from ingestion.ingest import run_ingest
from classification.classify import run_classify

def main():
    run_classify()
    run_ingest()



if __name__ == "__main__":
    main()