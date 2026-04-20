# 🧠 FAINANCE Smart Input

> AI backend for the FAINANCE financial advisor app — voice, invoices, and financial queries, handled end-to-end.

---

## ⚡ What It Does

| Feature | Input | Output |
|---|---|---|
| 🎙️ **Vietnamese ASR** | Audio file | Transcribed text + metadata |
| 🧾 **Invoice OCR** | Photo of receipt/invoice | Structured JSON (vendor, date, items, total) |
| 💬 **LLM Financial Parser** | Text / prompt | Extracted entities, categories, suggestions |

---

## 🔁 How It Works

```
🎙️ Audio  →  Gipformer (ASR)   →  Text ──┐
                                           ↓
🧾 Image  →  Vintern-1B (OCR)  →  Text ──→  LLM Parser / Extractor
                                           ↓
                                      📦 JSON → FAINANCE App
```

- **ASR** — [Gipformer 65M](https://huggingface.co/g-group-ai-lab/gipformer-65M-rnnt): lightweight ONNX/PyTorch model optimized for Vietnamese speech
- **OCR** — [Vintern-1B v3.5](https://huggingface.co/5CD-AI/Vintern-1B-v3_5): document-level vision-language model for invoice parsing
- **LLM** — OpenAI API or local Ollama for entity extraction and financial normalization
- **Server** — FastAPI application under `aicore/`

---

## 🗂️ Project Structure

```
aicore/          — FastAPI server, pipeline, ASR/LLM modules, utilities
gipformer/       — Gipformer inference code and examples (ONNX / PyTorch)
frontend-test/   — Minimal frontend demo for quick integration testing
```

---

## 🔌 API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/asr/recognize` | Upload audio → returns transcription and metadata |
| `POST` | `/ocr/invoice` | Upload image → returns structured invoice JSON |
| `POST` | `/ai/query` | Send text or prompt → returns financial extraction |

**Example — Invoice OCR response:**

```json
{
  "vendor": "Example Store",
  "date": "2026-04-15",
  "items": [{ "name": "Item A", "qty": 1, "price": 12.50 }],
  "currency": "VND",
  "total": 125000
}
```


## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🐍 Runtime | Python 3.8+ |
| ⚙️ Framework | FastAPI + Uvicorn |
| 🎙️ ASR | Gipformer 65M (ONNX / PyTorch) |
| 🧾 OCR | Vintern-1B v3.5 |
| 🤖 LLM | OpenAI API / Ollama|
| 🖥️ Hardware | GPU recommended; CPU supported |

---

## 🤝 Acknowledgements

This project builds on the work of outstanding open-source teams and researchers. We are grateful to:

---

### 🎙️ Gipformer — Vietnamese ASR

Efficient, lightweight automatic speech recognition model purpose-built for Vietnamese, developed by **G-Group AI Lab**.

- 🤗 Model card: [g-group-ai-lab/gipformer-65M-rnnt](https://huggingface.co/g-group-ai-lab/gipformer-65M-rnnt)
- 💻 Source repo: [github.com/ggroup-ai-lab/gipformer](https://github.com/ggroup-ai-lab/gipformer)

---

### 🧾 Vintern-1B v3.5 — Vietnamese Vision-Language Model

A compact yet capable multimodal LLM for document understanding and OCR, developed by **5CD-AI**.

- 🤗 Model card: [5CD-AI/Vintern-1B-v3_5](https://huggingface.co/5CD-AI/Vintern-1B-v3_5)

---

### 💼 FinancialAdvisor (FAINANCE)

This backend is designed to power the FAINANCE mobile application.

- 📱 App repo: [github.com/lhnam06/FinancialAdvisor](https://github.com/lhnam06/FinancialAdvisor)

---

## 📄 License

MIT — see `LICENSE` for details.