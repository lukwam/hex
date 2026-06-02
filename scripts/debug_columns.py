import io
from google.cloud import storage
import pdfplumber

PROJECT = "lukwam-hex"
BUCKET = "lukwam-hex-assets"
PDF_PATH = "puzzles/wsj/026mb6qKAGfBqarFYgmx/026mb6qKAGfBqarFYgmx_puzzle.pdf"

def main():
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(PDF_PATH)
    pdf_bytes = blob.download_as_bytes()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            print(f"\n=== PAGE {page_idx+1} ===")
            width = float(page.width)
            height = float(page.height)
            print(f"Page dimensions: {width} x {height}")
            words = page.extract_words()
            
            # Print total word count
            print(f"Total words on page: {len(words)}")
            
            # Filter words to middle range
            clue_words = [
                w for w in words
                if height * 0.22 < w["top"] < height * 0.88
            ]
            print(f"Words in middle range (22%-88%): {len(clue_words)}")
            
            # Print horizontal ranges for some words to see if they overlap
            # Let's print out the occupancy count
            occupancy = [0] * int(width + 1)
            for w in clue_words:
                x0 = max(0, int(w["x0"]))
                x1 = min(int(width), int(w["x1"]))
                for x in range(x0, x1 + 1):
                    if 0 <= x < len(occupancy):
                        occupancy[x] += 1
            
            # Print intervals of 0 occupancy (potential gutters)
            gutters = []
            in_gutter = False
            start_x = 0
            for x in range(len(occupancy)):
                if occupancy[x] == 0:
                    if not in_gutter:
                        in_gutter = True
                        start_x = x
                else:
                    if in_gutter:
                        in_gutter = False
                        end_x = x - 1
                        gutters.append((start_x, end_x, end_x - start_x))
            if in_gutter:
                gutters.append((start_x, int(width), int(width) - start_x))
                
            print("\nAll gutters (width >= 1):")
            for start, end, w in gutters:
                print(f"  Gutter from x={start} to x={end} (width: {w})")
                
            print("\nWords crossing x=120:")
            for w in clue_words:
                if w["x0"] < 120 < w["x1"]:
                    print(f"  '{w['text']}' at x0={w['x0']:.1f}, x1={w['x1']:.1f}, top={w['top']:.1f}, bottom={w['bottom']:.1f}")
                    
            print("\nWords crossing x=240:")
            for w in clue_words:
                if w["x0"] < 240 < w["x1"]:
                    print(f"  '{w['text']}' at x0={w['x0']:.1f}, x1={w['x1']:.1f}, top={w['top']:.1f}, bottom={w['bottom']:.1f}")

if __name__ == "__main__":
    main()
