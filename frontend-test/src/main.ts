interface RecorderState {
  mediaRecorder: MediaRecorder | null;
  chunks: BlobPart[];
  stream: MediaStream | null;
  startTime: number | null;
  timerInterval: ReturnType<typeof setInterval> | null;
  audioBlob: Blob | null;
}

interface AIResponse {
  status: string;
  input_type: string;
  raw_text: string;
  normalized_text?: string;
  result: {
    category: string;
    price: number;
    note: string;
  };
  message?: string;
}

const API_BASE_URL = 'http://localhost:8000';

class SimpleUI {
  private uploadArea: HTMLElement;
  private fileInput: HTMLInputElement;
  private imagePreview: HTMLImageElement;
  private uploadActions: HTMLElement;
  private cancelImageBtn: HTMLButtonElement;
  private submitImageBtn: HTMLButtonElement;
  private recordBtn: HTMLButtonElement;
  private stopBtn: HTMLButtonElement;
  private submitAudioBtn: HTMLButtonElement;
  private audioPlayback: HTMLAudioElement;
  private audioActions: HTMLElement;
  private playAudioBtn: HTMLButtonElement;
  private cancelAudioBtn: HTMLButtonElement;
  private recordingStatus: HTMLElement;
  private timer: HTMLElement;
  private resultContainer: HTMLElement;
  private resultContent: HTMLElement;
  private loadingOverlay: HTMLElement;
  private asrFileInput!: HTMLInputElement;
  private submitAsrBtn!: HTMLButtonElement;
  private asrStatus!: HTMLElement;
  private asrResult!: HTMLElement;
  private ocrResult: HTMLElement;
  private recording: RecorderState;
  private selectedImageFile: File | null = null;
  private selectedAsrFile: File | null = null;

  constructor() {
    this.uploadArea = document.getElementById('uploadArea')!;
    this.fileInput = document.getElementById('fileInput')! as HTMLInputElement;
    this.imagePreview = document.getElementById('imagePreview')! as HTMLImageElement;
    this.uploadActions = document.getElementById('uploadActions')!;
    this.cancelImageBtn = document.getElementById('cancelImageBtn')! as HTMLButtonElement;
    this.submitImageBtn = this.createSubmitButton('submitImageBtn', 'Xử lý ảnh');
    this.recordBtn = document.getElementById('recordBtn')! as HTMLButtonElement;
    this.stopBtn = document.getElementById('stopBtn')! as HTMLButtonElement;
    this.submitAudioBtn = this.createSubmitButton('submitAudioBtn', 'Xử lý âm thanh');
    this.audioPlayback = document.getElementById('audioPlayback')! as HTMLAudioElement;
    this.audioActions = document.getElementById('audioActions')!;
    this.playAudioBtn = document.getElementById('playAudioBtn')! as HTMLButtonElement;
    this.cancelAudioBtn = document.getElementById('cancelAudioBtn')! as HTMLButtonElement;
    this.recordingStatus = document.getElementById('recordingStatus')!;
    this.timer = document.getElementById('timer')!;
    this.resultContainer = this.createResultContainer();
    this.resultContent = document.getElementById('resultContent')!;
    this.loadingOverlay = this.createLoadingOverlay();
    this.ocrResult = document.getElementById('ocrResult')! as HTMLElement;

    this.recording = {
      mediaRecorder: null,
      chunks: [],
      stream: null,
      startTime: null,
      timerInterval: null,
      audioBlob: null,
    };

    this.initUpload();
    this.initRecording();
    this.initAsrUpload();
  }

  private initAsrUpload(): void {
    this.asrFileInput = document.getElementById('asrFileInput')! as HTMLInputElement;
    this.submitAsrBtn = document.getElementById('submitAsrBtn')! as HTMLButtonElement;
    this.asrStatus = document.getElementById('asrStatus')! as HTMLElement;
    this.asrResult = document.getElementById('asrResult')! as HTMLElement;

    this.asrFileInput.addEventListener('change', (e) => {
      const file = (e.target as HTMLInputElement).files?.[0] || null;
      if (file) {
        this.selectedAsrFile = file;
        this.submitAsrBtn.disabled = false;
        this.asrStatus.textContent = file.name;
      } else {
        this.selectedAsrFile = null;
        this.submitAsrBtn.disabled = true;
        this.asrStatus.textContent = '';
      }
    });

    this.submitAsrBtn.addEventListener('click', async () => {
      if (!this.selectedAsrFile) return;
      this.asrStatus.textContent = 'Sending...';
      this.setProcessingState(true);
      try {
        await this.processAudioFile(this.selectedAsrFile);
      } finally {
        this.setProcessingState(false);
        this.submitAsrBtn.disabled = !this.selectedAsrFile;
        this.asrStatus.textContent = '';
      }
    });
  }

  private async processAudioFile(file: File): Promise<void> {
    this.showLoading();
    try {
      const formData = new FormData();
      formData.append('file', file, file.name);

      const response = await fetch(`${API_BASE_URL}/api/process/audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: AIResponse = await response.json();
      // show ASR result area too
      if (data.raw_text) {
        this.asrResult.style.display = 'block';
        this.asrResult.innerHTML = `<strong>Transcription:</strong><div style="margin-top:8px;">${data.raw_text}</div>`;
      } else {
        this.asrResult.style.display = 'block';
        this.asrResult.innerHTML = `<div style="color:#f44336">No transcription returned.</div>`;
      }
      this.displayResult(data);
    } catch (error) {
      console.error('Error uploading ASR file:', error);
      this.asrResult.style.display = 'block';
      this.asrResult.innerHTML = `<div style="color:#f44336">Lỗi khi gửi file ASR. Vui lòng thử lại.</div>`;
    } finally {
      this.hideLoading();
    }
  }

  private createSubmitButton(id: string, text: string): HTMLButtonElement {
    const btn = document.createElement('button');
    btn.id = id;
    btn.className = 'submit-btn';
    btn.textContent = text;
    btn.style.cssText = `
      padding: 12px 24px;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.2s;
    `;
    btn.addEventListener('mouseenter', () => btn.style.background = '#45a049');
    btn.addEventListener('mouseleave', () => btn.style.background = '#4CAF50');
    return btn;
  }

  private createResultContainer(): HTMLElement {
    const container = document.createElement('div');
    container.id = 'resultContainer';
    container.style.cssText = `
      margin-top: 30px;
      padding: 20px;
      background: #f9f9f9;
      border-radius: 12px;
      display: none;
    `;
    
    const title = document.createElement('h3');
    title.textContent = 'Kết quả xử lý';
    title.style.cssText = 'margin: 0 0 15px 0; color: #333;';
    
    const content = document.createElement('div');
    content.id = 'resultContent';
    content.style.cssText = 'background: white; padding: 15px; border-radius: 8px;';
    
    container.appendChild(title);
    container.appendChild(content);
    document.querySelector('.container')?.appendChild(container);
    
    return container;
  }

  private createLoadingOverlay(): HTMLElement {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    `;
    
    const spinner = document.createElement('div');
    spinner.style.cssText = `
      width: 50px;
      height: 50px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #4CAF50;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    `;
    
    const style = document.createElement('style');
    style.textContent = `
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
    
    overlay.appendChild(spinner);
    document.body.appendChild(overlay);
    
    return overlay;
  }

  private showLoading(): void {
    this.loadingOverlay.style.display = 'flex';
  }

  private hideLoading(): void {
    this.loadingOverlay.style.display = 'none';
  }

  private setProcessingState(isProcessing: boolean): void {
    this.submitImageBtn.disabled = isProcessing || !this.selectedImageFile;
    this.submitAudioBtn.disabled = isProcessing || !this.recording.audioBlob;
    this.submitAsrBtn.disabled = isProcessing || !this.selectedAsrFile;
      this.recordBtn.disabled = isProcessing || (!!this.recording.mediaRecorder && this.recording.mediaRecorder.state === 'recording');
    this.stopBtn.disabled = isProcessing || !this.recording.mediaRecorder || this.recording.mediaRecorder.state !== 'recording';
    this.playAudioBtn.disabled = isProcessing || !this.recording.audioBlob;
    this.cancelImageBtn.disabled = isProcessing;
    this.cancelAudioBtn.disabled = isProcessing || !this.recording.audioBlob;
    this.asrFileInput.disabled = isProcessing;
    this.fileInput.disabled = isProcessing;
  }

  private displayResult(response: AIResponse): void {
    this.resultContent.innerHTML = '';
    // reset section-specific result displays
    if (this.ocrResult) {
      this.ocrResult.style.display = 'none';
      this.ocrResult.innerHTML = '';
    }
    if (this.asrResult) {
      this.asrResult.style.display = 'none';
      this.asrResult.innerHTML = '';
    }
    
    if (response.status === 'error') {
      this.resultContent.innerHTML = `
        <div style="color: #f44336; padding: 10px;">
          <strong>Lỗi:</strong> ${response.message || 'Không thể xử lý'}
        </div>
      `;
    } else {
      const { result, raw_text, input_type } = response;

      // show OCR/ASR in section-specific cards only
      if (raw_text) {
        if (input_type === 'image') {
          if (this.ocrResult) {
            this.ocrResult.style.display = 'block';
            this.ocrResult.innerHTML = `<strong>OCR:</strong><div style="margin-top:8px; white-space:pre-wrap">${raw_text}</div>`;
          }
        } else {
          if (this.asrResult) {
            this.asrResult.style.display = 'block';
            this.asrResult.innerHTML = `<strong>ASR:</strong><div style="margin-top:8px; white-space:pre-wrap">${raw_text}</div>`;
          }
        }
      }
      
      const html = `
        <div style="margin-bottom: 15px;">
          <strong>Loại input:</strong> ${input_type === 'image' ? '📷 Ảnh' : '🎤 Âm thanh'}
        </div>
        ${response.raw_text ? `
        <div style="margin-bottom: 15px;">
          <strong>Văn bản nhận diện:</strong>
          <div style="background: #fff8e1; padding: 10px; border-radius: 6px; margin-top: 5px; color: #333;">
            ${response.raw_text}
          </div>
        </div>
        ` : ''}
        ${response.normalized_text ? `
        <div style="margin-bottom: 15px;">
          <strong>Văn bản đã chuẩn hóa:</strong>
          <div style="background: #f5f5f5; padding: 10px; border-radius: 6px; margin-top: 5px;">
            ${response.normalized_text}
          </div>
        </div>
        ` : ''}
        <div style="border-top: 2px solid #4CAF50; padding-top: 15px;">
          <h4 style="margin: 0 0 10px 0; color: #4CAF50;">Kết quả phân tích</h4>
          <div style="display: grid; gap: 10px;">
            <div>
              <strong>Danh mục:</strong>
              <span style="background: #e3f2fd; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-left: 8px;">
                ${result.category}
              </span>
            </div>
            <div>
              <strong>Số tiền:</strong>
              <span style="color: #f44336; font-weight: bold; margin-left: 8px;">
                ${result.price.toLocaleString('vi-VN')} ₫
              </span>
            </div>
            <div>
              <strong>Ghi chú:</strong>
              <span style="margin-left: 8px;">${result.note}</span>
            </div>
          </div>
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
          <strong>JSON (full response):</strong>
          <pre style="background: #263238; color: #aed581; padding: 10px; border-radius: 6px; margin-top: 5px; overflow-x: auto;">
${JSON.stringify(response, null, 2)}
          </pre>
        </div>
      `;
      this.resultContent.innerHTML = html;
    }
    
    this.resultContainer.style.display = 'block';
  }

  private async processImage(file: File): Promise<void> {
    this.setProcessingState(true);
    this.showLoading();
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/api/process/image`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: AIResponse = await response.json();
      this.displayResult(data);
    } catch (error) {
      console.error('Error processing image:', error);
      this.displayResult({
        status: 'error',
        input_type: 'image',
        raw_text: '',
        result: { category: 'khác', price: 0, note: '' },
        message: 'Lỗi khi xử lý ảnh. Vui lòng thử lại.'
      });
    } finally {
      this.hideLoading();
      this.setProcessingState(false);
    }
  }

  private async processAudio(blob: Blob): Promise<void> {
    this.setProcessingState(true);
    this.showLoading();
    
    try {
      const formData = new FormData();
      const file = new File([blob], 'recording.webm', { type: blob.type });
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/api/process/audio`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: AIResponse = await response.json();
      this.displayResult(data);
    } catch (error) {
      console.error('Error processing audio:', error);
      this.displayResult({
        status: 'error',
        input_type: 'audio',
        raw_text: '',
        result: { category: 'khác', price: 0, note: '' },
        message: 'Lỗi khi xử lý âm thanh. Vui lòng thử lại.'
      });
    } finally {
      this.hideLoading();
      this.setProcessingState(false);
    }
  }

  private initUpload(): void {
    this.uploadArea.addEventListener('click', () => {
      this.fileInput.click();
    });

    this.uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      this.uploadArea.style.borderColor = '#4CAF50';
    });

    this.uploadArea.addEventListener('dragleave', () => {
      this.uploadArea.style.borderColor = '#ccc';
    });

    this.uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      this.uploadArea.style.borderColor = '#ccc';
      const file = e.dataTransfer?.files[0];
      if (file && file.type.startsWith('image/')) {
        this.handleFile(file);
      }
    });

    this.fileInput.addEventListener('change', (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        this.handleFile(file);
      }
    });

    this.cancelImageBtn.addEventListener('click', () => {
      this.resetUpload();
    });

    this.submitImageBtn.addEventListener('click', () => {
      if (this.selectedImageFile) {
        this.processImage(this.selectedImageFile);
      }
    });
    this.submitImageBtn.disabled = true;
  }

  private handleFile(file: File): void {
    this.selectedImageFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      this.imagePreview.src = e.target?.result as string;
      this.imagePreview.style.display = 'block';
      this.uploadArea.classList.add('has-image');
      const icon = this.uploadArea.querySelector('.upload-icon') as HTMLElement;
      const text = this.uploadArea.querySelector('.upload-text') as HTMLElement;
      if (icon) icon.style.display = 'none';
      if (text) text.style.display = 'none';
      this.uploadActions.style.display = 'flex';
      this.uploadActions.style.gap = '10px';
      
      if (!this.submitImageBtn.parentNode) {
        this.uploadActions.appendChild(this.submitImageBtn);
      }
      this.submitImageBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  private resetUpload(): void {
    this.selectedImageFile = null;
    this.imagePreview.src = '';
    this.imagePreview.style.display = 'none';
    this.uploadArea.classList.remove('has-image');
    const icon = this.uploadArea.querySelector('.upload-icon') as HTMLElement;
    const text = this.uploadArea.querySelector('.upload-text') as HTMLElement;
    if (icon) icon.style.display = 'block';
    if (text) text.style.display = 'block';
    this.uploadActions.style.display = 'none';
    this.fileInput.value = '';
    this.submitImageBtn.disabled = true;
  }

  private async initRecording(): Promise<void> {
    this.recordBtn.addEventListener('click', async () => {
      await this.startRecording();
    });

    this.stopBtn.addEventListener('click', () => {
      this.stopRecording();
    });

    this.playAudioBtn.addEventListener('click', () => {
      this.audioPlayback.play();
    });

    this.cancelAudioBtn.addEventListener('click', () => {
      this.resetRecording();
    });

    this.submitAudioBtn.addEventListener('click', () => {
      if (this.recording.audioBlob) {
        this.processAudio(this.recording.audioBlob);
      }
    });
    this.submitAudioBtn.disabled = true;
    this.playAudioBtn.disabled = true;
    this.cancelAudioBtn.disabled = true;
  }

  private async startRecording(): Promise<void> {
    try {
      this.recording.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.recording.mediaRecorder = new MediaRecorder(this.recording.stream);
      this.recording.chunks = [];

      this.recording.mediaRecorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) {
          this.recording.chunks.push(e.data);
        }
      };

      this.recording.mediaRecorder.onstop = () => {
        const blob = new Blob(this.recording.chunks, { type: 'audio/webm' });
        // Convert to WAV and set as the recording blob
        this.convertBlobToWav(blob)
          .then((wavBlob) => {
            this.recording.audioBlob = wavBlob;
            const url = URL.createObjectURL(wavBlob);
            this.audioPlayback.src = url;
            this.audioPlayback.style.display = 'block';
            this.audioActions.style.display = 'flex';
            this.audioActions.style.gap = '10px';

            if (!this.submitAudioBtn.parentNode) {
              this.audioActions.appendChild(this.submitAudioBtn);
            }
            this.submitAudioBtn.disabled = false;
            this.playAudioBtn.disabled = false;
            this.cancelAudioBtn.disabled = false;

            if (this.recording.stream) {
              this.recording.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
            }
          })
          .catch((err) => {
            console.error('WAV conversion failed, using original blob', err);
            this.recording.audioBlob = blob;
            const url = URL.createObjectURL(blob);
            this.audioPlayback.src = url;
            this.audioPlayback.style.display = 'block';
            this.audioActions.style.display = 'flex';
            this.audioActions.style.gap = '10px';

            if (!this.submitAudioBtn.parentNode) {
              this.audioActions.appendChild(this.submitAudioBtn);
            }
            this.submitAudioBtn.disabled = false;
            this.playAudioBtn.disabled = false;
            this.cancelAudioBtn.disabled = false;

            if (this.recording.stream) {
              this.recording.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
            }
          });
      };

      this.recording.mediaRecorder.start();
      this.recording.startTime = Date.now();

      this.recordBtn.disabled = true;
      this.recordBtn.classList.add('recording');
      this.stopBtn.disabled = false;
      this.recordingStatus.textContent = 'Recording...';

      this.recording.timerInterval = setInterval(() => {
        this.updateTimer();
      }, 1000);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Please check permissions.');
    }
  }

  private stopRecording(): void {
    if (this.recording.mediaRecorder && this.recording.mediaRecorder.state !== 'inactive') {
      this.recording.mediaRecorder.stop();
    }

    this.recordBtn.disabled = false;
    this.recordBtn.classList.remove('recording');
    this.stopBtn.disabled = true;
    this.recordingStatus.textContent = '';

    if (this.recording.timerInterval) {
      clearInterval(this.recording.timerInterval);
    }

    this.timer.textContent = '00:00';
  }

  private resetRecording(): void {
    this.audioPlayback.src = '';
    this.audioPlayback.style.display = 'none';
    this.audioActions.style.display = 'none';
    this.recording.audioBlob = null;
    this.recording.chunks = [];
    this.submitAudioBtn.disabled = true;
    this.playAudioBtn.disabled = true;
    this.cancelAudioBtn.disabled = true;
  }

  private updateTimer(): void {
    if (!this.recording.startTime) return;

    const elapsed = Math.floor((Date.now() - this.recording.startTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    this.timer.textContent = `${minutes}:${seconds}`;
  }

  private async convertBlobToWav(blob: Blob): Promise<Blob> {
    const arrayBuffer = await blob.arrayBuffer();
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;

    // Interleave channels
    let interleaved: Float32Array;
    if (numChannels === 1) {
      interleaved = audioBuffer.getChannelData(0);
    } else {
      const len = audioBuffer.length;
      interleaved = new Float32Array(len * numChannels);
      for (let i = 0; i < len; i++) {
        for (let ch = 0; ch < numChannels; ch++) {
          interleaved[i * numChannels + ch] = audioBuffer.getChannelData(ch)[i];
        }
      }
    }

    const buffer = new ArrayBuffer(44 + interleaved.length * 2);
    const view = new DataView(buffer);

    function writeString(view: DataView, offset: number, str: string) {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    }

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + interleaved.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, interleaved.length * 2, true);

    let offset = 44;
    for (let i = 0; i < interleaved.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, interleaved[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }
}

new SimpleUI();
