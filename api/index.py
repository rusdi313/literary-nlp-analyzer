from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import json
import re
from nltk.stem import SnowballStemmer
import nltk
from nltk import pos_tag
from nltk.tokenize import word_tokenize

import os
nltk_data_dir = "/tmp/nltk_data"
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir, exist_ok=True)
if nltk_data_dir not in nltk.data.path:
    nltk.data.path.append(nltk_data_dir)

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('taggers/averaged_perceptron_tagger')
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('punkt', download_dir=nltk_data_dir)
    nltk.download('punkt_tab', download_dir=nltk_data_dir)
    nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir)
    nltk.download('averaged_perceptron_tagger_eng', download_dir=nltk_data_dir)

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

stemmer = SnowballStemmer("english")
STEMMED_LEXICON = {theme: {w: stemmer.stem(w) for w in words} for theme, words in LEXICON.items()}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    text_content = ""
    # Process PDF file directly from uploaded memory
    with pdfplumber.open(file.file) as pdf:
        # Extract from all pages
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
    
    # Process text content
    analysis = analyze_text(text_content, file.filename)
    
    return {
        "filename": file.filename,
        "analysis": analysis
    }

def analyze_text(text: str, filename: str = ""):
    # Total words
    words = re.findall(r'\b\w+\b', text.lower())
    total_words = len(words)
    if total_words == 0:
        total_words = 1
        
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
    
    negations = {"not", "no", "never", "none", "neither", "nor", "without"}
    
    for chunk in chunks:
        tokens = word_tokenize(chunk)
        tokens_lower = [t.lower() for t in tokens]
        pos_tags = pos_tag(tokens_lower)
        stems = [stemmer.stem(w) for w in tokens_lower]
        
        chunk_scores = {k: 0 for k in LEXICON.keys()}
        chunk_matched_words = {k: set() for k in LEXICON.keys()}
        
        for i, (word, tag) in enumerate(pos_tags):
            stem_w = stems[i]
            for theme, word_map in STEMMED_LEXICON.items():
                for original_w, dict_stem in word_map.items():
                    if stem_w == dict_stem:
                        is_valid_pos = tag.startswith('NN') or tag.startswith('VB') or tag.startswith('JJ')
                        
                        has_negation = False
                        start_idx = max(0, i - 3)
                        preceding_words = tokens_lower[start_idx:i]
                        if any(neg in preceding_words for neg in negations):
                            has_negation = True
                            
                        if is_valid_pos and not has_negation:
                            chunk_scores[theme] += 1
                            theme_scores[theme] += 1
                            
                            if original_w not in theme_breakdown[theme]["keywords"]:
                                theme_breakdown[theme]["keywords"][original_w] = 0
                            theme_breakdown[theme]["keywords"][original_w] += 1
                            chunk_matched_words[theme].add(original_w)
        
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
    
    # Calculate Final Intensity Score based on Validated Keywords and Total Words
    for theme in theme_scores:
        validated_count = theme_scores[theme]
        
        # Calculate Intensity Score (Normalized per 10,000 words)
        intensity_score = round((validated_count / total_words) * 10000, 1)
        theme_scores[theme] = intensity_score
        

    return {
        "theme_scores": theme_scores,
        "dominant_themes": [{"theme": t[0], "score": t[1]} for t in top_overall],
        "theme_breakdown": theme_breakdown,
        "interpretation": interpretation
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
