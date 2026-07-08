from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LEXICON = {
    "body": ["body", "skin", "face", "hair", "breast", "womb", "blood", "hands", "arms", "thighs", "belly"],
    "reproduction": ["mother", "child", "baby", "birth", "pregnancy", "womb", "fertility", "ovaries", "milk", "daughter"],
    "sexuality": ["sex", "desire", "touch", "kiss", "love", "shame", "rape", "pleasure", "marriage", "naked"],
    "control": ["law", "police", "state", "commander", "master", "caste", "family", "religion", "rule", "order"],
    "violence": ["beat", "hit", "kill", "cut", "drag", "rape", "dirty", "wound", "blood", "pain"],
    "shame": ["shame", "sin", "dirty", "illegitimate", "disgrace", "immoral", "forbidden"],
    "resistance": ["escape", "refuse", "remember", "speak", "love", "choose", "survive", "freedom"]
}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    text_content = ""
    # Process PDF file directly from uploaded memory
    with pdfplumber.open(file.file) as pdf:
        # Extract from first 30 pages for MVP speed (often enough for initial mapping)
        # Using a higher page limit to get good data, but avoiding whole book parsing for speed
        for i, page in enumerate(pdf.pages):
            if i > 30: 
                break
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
    
    # Process text content
    analysis = analyze_text(text_content)
    
    return {
        "filename": file.filename,
        "analysis": analysis
    }

def analyze_text(text: str):
    # Chunking: split by paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 30] # Simple chunking
    
    # Regroup into larger chunks (e.g. 5 lines)
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        current_chunk += p + " "
        if len(current_chunk) > 300:
            chunks.append(current_chunk.strip())
            current_chunk = ""
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    theme_scores = {k: 0 for k in LEXICON.keys()}
    theme_breakdown = {k: {"keywords": {}, "snippets": []} for k in LEXICON.keys()}
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        chunk_scores = {k: 0 for k in LEXICON.keys()}
        chunk_matched_words = {k: set() for k in LEXICON.keys()}
        
        for theme, words in LEXICON.items():
            for w in words:
                matches = len(re.findall(r'\b' + w + r'\b', chunk_lower))
                if matches > 0:
                    chunk_scores[theme] += matches
                    theme_scores[theme] += matches
                    
                    if w not in theme_breakdown[theme]["keywords"]:
                        theme_breakdown[theme]["keywords"][w] = 0
                    theme_breakdown[theme]["keywords"][w] += matches
                    chunk_matched_words[theme].add(w)
        
        for theme, score in chunk_scores.items():
            if score > 0:
                # Store snippets per theme (max 8 per theme)
                if len(theme_breakdown[theme]["snippets"]) < 8:
                    theme_breakdown[theme]["snippets"].append({
                        "text": chunk,
                        "matched_words": list(chunk_matched_words[theme]),
                        "score": score
                    })

    # Sort snippets by score
    for theme in theme_breakdown.keys():
        theme_breakdown[theme]["snippets"] = sorted(theme_breakdown[theme]["snippets"], key=lambda x: x["score"], reverse=True)
    
    # Mocking feminist interpretation based on top themes
    top_overall = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    top_theme_names = [t[0] for t in top_overall]
    
    interpretation = "The text features themes of " + ", ".join(top_theme_names) + "."
    if "reproduction" in top_theme_names and "control" in top_theme_names:
        interpretation = "The female body is framed as a reproductive object controlled by the state or societal norms."
    elif "violence" in top_theme_names and "body" in top_theme_names:
        interpretation = "The body is represented as a site of violence and trauma."
    elif "sexuality" in top_theme_names and "shame" in top_theme_names:
        interpretation = "Female sexuality is regulated by social institutions and moral judgment."
    elif "reproduction" in top_theme_names:
        interpretation = "Motherhood and reproduction play a central role, intertwined with the character's agency or trauma."
    
    return {
        "theme_scores": theme_scores,
        "dominant_themes": [{"theme": t[0], "score": t[1]} for t in top_overall],
        "theme_breakdown": theme_breakdown,
        "interpretation": interpretation
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
