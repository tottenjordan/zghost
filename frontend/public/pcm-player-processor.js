/**
 * AudioWorklet processor for continuous PCM audio playback.
 * Uses a ring buffer to stream audio samples without gaps or artifacts.
 *
 * Based on the working reference implementation from ge_grocery_store.
 */
class PCMPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Ring buffer sized for 10 seconds at 24kHz
    this.bufferSize = 24000 * 10;
    this.buffer = new Float32Array(this.bufferSize);
    this.readIndex = 0;
    this.writeIndex = 0;
    this.draining = false;

    this.port.onmessage = (event) => {
      if (event.data.command === 'endOfAudio') {
        // Let the buffer drain naturally instead of flushing unplayed audio
        this.draining = true;
        return;
      }
      if (event.data.command === 'clear') {
        this.readIndex = 0;
        this.writeIndex = 0;
        this.draining = false;
        this.buffer.fill(0);
        return;
      }
      // New data arriving cancels drain mode
      this.draining = false;
      // Incoming data is raw Int16 PCM samples as ArrayBuffer
      const int16Samples = new Int16Array(event.data);
      this._enqueue(int16Samples);
    };
  }

  _enqueue(int16Samples) {
    for (let i = 0; i < int16Samples.length; i++) {
      const floatVal = int16Samples[i] / 32768;
      this.buffer[this.writeIndex] = floatVal;
      this.writeIndex = (this.writeIndex + 1) % this.bufferSize;
      // If write catches up to read, advance read (drop oldest samples)
      if (this.writeIndex === this.readIndex) {
        this.readIndex = (this.readIndex + 1) % this.bufferSize;
      }
    }
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const framesPerBlock = output[0].length;
    for (let frame = 0; frame < framesPerBlock; frame++) {
      if (this.readIndex !== this.writeIndex) {
        const sample = this.buffer[this.readIndex];
        output[0][frame] = sample;
        if (output.length > 1) output[1][frame] = sample;
        this.readIndex = (this.readIndex + 1) % this.bufferSize;
      } else {
        // Buffer empty — output silence
        output[0][frame] = 0;
        if (output.length > 1) output[1][frame] = 0;
      }
    }
    return true;
  }
}

registerProcessor('pcm-player-processor', PCMPlayerProcessor);
