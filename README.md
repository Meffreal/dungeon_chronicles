# Dungeon Chronicles

## Požadavky
- Python 3.11+
- pip

---

# Install
cd backend
pip install -r requirements.txt
```

## 2. Spuštění serveru

```bash
cd backend
uvicorn main:app --reload --port 8000
```

## 4. API dokumentace

FastAPI automaticky generuje dokumentaci:
```
http://localhost:8000/docs
```

---

/*
 You are a senior backend/frontend game developer and head of game development.
 Read the official DiceBear Adventurer documentation here:
 https://www.dicebear.com/styles/adventurer/
 Find all valid appearance and customization options supported by this style
 and implement them into our game avatar generation system.

 Only include options that are valid according to the documentation.
 Remove any appearance options that are not listed or supported for DiceBear Adventurer.

 The valid appearance options include:
   - seed (string)
   - flip (boolean)
   - rotate (integer 0-360)
   - scale (integer 0-200)
   - radius (integer 0-50)
   - size (integer >=1)
   - backgroundColor (array of hex or "transparent")
   - backgroundType (array: gradientLinear, solid)
   - backgroundRotation (array [min, max])
   - translateX (integer -100 to 100)
   - translateY (integer -100 to 100)
   - clip (boolean)
   - randomizeIds (boolean)
   - base (array: default)
   - earrings (array: variant01..variant06)
   - earringsProbability (integer 0-100)
   - eyebrows (array: variant01..variant15)
   - eyes (array: variant01..variant26)
   - features (array: birthmark, blush, freckles, mustache)
   - featuresProbability (integer 0-100)
   - glasses (array: variant01..variant05)
   - glassesProbability (integer 0-100)
   - hair (array: long01..long26, short01..short19)
   - hairColor (array of hex color strings or transparent)
   - hairProbability (integer 0-100)
   - mouth (array: variant01..variant30)
   - skinColor (array of hex color strings or transparent)

 Generate code for both backend (API integration / generation logic) and frontend (UI controls to pick these options). Make sure all fields are validated against documented limits/types.
*/