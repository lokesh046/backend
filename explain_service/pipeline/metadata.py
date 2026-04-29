import datetime

def generate_metadata(filename, category="general", version=1):
    return {
        "source": filename,
        "upload_time": str(datetime.datetime.now()),
        "category": category,
        "version": version
    }
