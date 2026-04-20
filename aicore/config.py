import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR

# Model paths
MODELS_DIR = BASE_DIR / "models"

# ASR configuration: we use Gipformer (HuggingFace) as the ASR provider.
ASR_CONFIG = {
    "provider": "gipformer",
    "num_threads": 4,
    "decoding_method": "modified_beam_search",
    "sample_rate": 16000,
    "feature_dim": 80,
}

# OCR Model (Vintern)
OCR_MODEL_NAME = "5CD-AI/Vintern-1B-v3_5"
OCR_CONFIG = {
    "torch_dtype": "float16",
    "trust_remote_code": True,
    "use_flash_attn": False,
    "image_size": 448,
    "max_num_patches": 5,
}

LLM_CONFIG = {
    "provider": "ollama",
}

OLLAMA_CONFIG = {
    "host": os.getenv("OLLAMA_HOST", "http://localhost:11434").strip(),
    "api_key": os.getenv("OLLAMA_API_KEY", "").strip(),
    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip(),
    "timeout_seconds": int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")),
}

# System prompt for expense parsing
EXPENSE_SYSTEM_PROMPT = """
Bạn là parser chi tiêu. Suy nghĩ ngắn rồi trả về JSON.

Schema: {"category": string, "price": integer, "note": string}

Phân loại:
ăn uống | mua sắm | đi lại | giải trí | học tập | nhà cửa | y tế | khác

Quy tắc giá (nghìn/ngàn/ca = x1000, triệu/tr = x1000000):
"ba ngàn"                          = 3000
"bảy mươi tám ngàn"                = 78000
"một trăm hai mươi ngàn"           = 120000
"bốn trăm hai mươi ngàn"           = 420000
"một triệu rưỡi"                   = 1500000
"mười hai triệu"                   = 12000000
"năm mươi triệu"                   = 50000000
"hai trăm triệu"                   = 200000000

Ví dụ input/output:
input: "mua kẹo ba ngàn"
think: kẹo là ăn uống, ba ngàn = 3000
output: {"category":"ăn uống","price":3000,"note":"kẹo"}

input: "đổ xăng một trăm hai mươi ngàn"
think: xăng là đi lại, một trăm hai mươi ngàn = 120000
output: {"category":"đi lại","price":120000,"note":"xăng"}

input: "ăn bún bò bốn trăm hai mươi ngàn"
think: bún bò là ăn uống, bốn trăm hai mươi ngàn = 420000
output: {"category":"ăn uống","price":420000,"note":"bún bò"}

input: "mua điện thoại mười hai triệu"
think: điện thoại là mua sắm, mười hai triệu = 12000000
output: {"category":"mua sắm","price":12000000,"note":"điện thoại"}

input: "sửa nhà hai trăm triệu"
think: sửa nhà là nhà cửa, hai trăm triệu = 200000000
output: {"category":"nhà cửa","price":200000000,"note":"sửa nhà"}
""".strip()

# OCR prompt
OCR_PROMPT = """Trích xuất dạng đoạn văn tóm tắt thông tin hóa đơn, Nói cực ngắn gọn"""
OCR_PROMPT_2 = """Trích xuất từ ảnh thông tin số tiền sau cùng (đã giảm giá, trừ thuế (nếu có)). Format lại thành JSON theo schema sau, không cần giải thích gì thêm:
{
  'category': <'' (để trống)>,
  'price': <số nguyên thuần, ví dụ 54420000 hoặc 7944000, hoặc 2345000, hoặc 890000 hoặc 19000>,
  'note': <Ghi chú về tên món/dịch vụ/quán ăn>,
}"""
# Server config
ENV = os.getenv("AICORE_ENV", "production").strip().lower()
SERVER_HOST = os.getenv("AICORE_HOST", "0.0.0.0").strip()
SERVER_PORT = int(os.getenv("AICORE_PORT", "8000"))
SERVER_RELOAD = os.getenv("AICORE_RELOAD", "false").strip().lower() == "true"
UVICORN_WORKERS = int(os.getenv("AICORE_UVICORN_WORKERS", "1"))

# API request limits (MB)
MAX_IMAGE_MB = int(os.getenv("AICORE_MAX_IMAGE_MB", "10"))
MAX_AUDIO_MB = int(os.getenv("AICORE_MAX_AUDIO_MB", "20"))

# GPU queue controls
GPU_QUEUE_MAXSIZE = int(os.getenv("AICORE_GPU_QUEUE_MAXSIZE", "64"))
GPU_WORKERS = int(os.getenv("AICORE_GPU_WORKERS", "1"))
REQUEST_TIMEOUT_SEC = int(os.getenv("AICORE_REQUEST_TIMEOUT_SEC", "120"))

# CORS
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("AICORE_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

# Logging
LOG_LEVEL = os.getenv("AICORE_LOG_LEVEL", "INFO").strip().upper()
LOG_FORMAT = os.getenv(
    "AICORE_LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
