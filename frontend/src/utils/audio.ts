/**
 * Custom Web Audio API SFX Synthesizer
 * Generates thematic gothic sound effects dynamically to keep assets lightweight and avoid dependency errors.
 */

let audioCtx: AudioContext | null = null;

function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

export function playInspectSFX() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // 根谐振节点
    const filter = ctx.createBiquadFilter();
    filter.type = "peaking";
    filter.frequency.value = 1200;
    filter.Q.value = 5;
    filter.connect(ctx.destination);

    // 空灵上升频率振荡器
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.exponentialRampToValueAtTime(1800, now + 1.2);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.25, now + 0.15);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 1.4);

    osc.connect(gain);
    gain.connect(filter);
    osc.start(now);
    osc.stop(now + 1.5);

    // 二级闪烁调制
    const mod = ctx.createOscillator();
    mod.type = "triangle";
    mod.frequency.setValueAtTime(880, now);
    mod.frequency.linearRampToValueAtTime(2200, now + 1.0);

    const modGain = ctx.createGain();
    modGain.gain.setValueAtTime(0, now);
    modGain.gain.linearRampToValueAtTime(0.12, now + 0.3);
    modGain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);

    mod.connect(modGain);
    modGain.connect(filter);
    mod.start(now);
    mod.stop(now + 1.3);
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}

export function playHealSFX() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    const delay = ctx.createDelay();
    delay.delayTime.value = 0.25;

    const feedback = ctx.createGain();
    feedback.gain.value = 0.4;

    delay.connect(feedback);
    feedback.connect(delay);
    delay.connect(ctx.destination);

    // 和谐大三和弦钟声序列
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + idx * 0.15);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, now + idx * 0.15);
      gain.gain.linearRampToValueAtTime(0.2, now + idx * 0.15 + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.15 + 1.0);

      osc.connect(gain);
      gain.connect(ctx.destination);
      gain.connect(delay);

      osc.start(now + idx * 0.15);
      osc.stop(now + idx * 0.15 + 1.1);
    });
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // 低沉气泡振荡器
    const bOsc = ctx.createOscillator();
    bOsc.type = "sawtooth";
    bOsc.frequency.setValueAtTime(65, now);
    bOsc.frequency.linearRampToValueAtTime(45, now + 1.8);

    // 酸性气泡带通扫频滤波器
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(250, now);
    filter.Q.value = 8;
    filter.connect(ctx.destination);

    // 气泡 LFO
    const lfo = ctx.createOscillator();
    lfo.type = "sawtooth";
    lfo.frequency.setValueAtTime(14, now); // bubbling speed

    const lfoGain = ctx.createGain();
    lfoGain.gain.setValueAtTime(180, now);

    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);

    const pGain = ctx.createGain();
    pGain.gain.setValueAtTime(0, now);
    pGain.gain.linearRampToValueAtTime(0.35, now + 0.2);
    pGain.gain.exponentialRampToValueAtTime(0.005, now + 2.0);

    bOsc.connect(pGain);
    pGain.connect(filter);

    lfo.start(now);
    bOsc.start(now);

    lfo.stop(now + 2.1);
    bOsc.stop(now + 2.1);

    // 死亡嘶嘶声
    const bufferSize = ctx.sampleRate * 1.5;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = "lowpass";
    noiseFilter.frequency.setValueAtTime(8000, now);
    noiseFilter.frequency.exponentialRampToValueAtTime(200, now + 1.5);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0, now);
    noiseGain.gain.linearRampToValueAtTime(0.06, now + 0.4);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 1.5);

    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(ctx.destination);

    noise.start(now + 0.2);
    noise.stop(now + 1.8);
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}

export function playBiteSFX() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // 低沉咆哮
    const osc1 = ctx.createOscillator();
    osc1.type = "sawtooth";
    osc1.frequency.setValueAtTime(90, now);
    osc1.frequency.linearRampToValueAtTime(45, now + 0.8);

    const gain1 = ctx.createGain();
    gain1.gain.setValueAtTime(0.4, now);
    gain1.gain.exponentialRampToValueAtTime(0.005, now + 0.9);

    const filter1 = ctx.createBiquadFilter();
    filter1.type = "lowpass";
    filter1.frequency.setValueAtTime(180, now);

    osc1.connect(filter1);
    filter1.connect(gain1);
    gain1.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 1.0);

    // 血肉撕裂声（滤波噪声）
    const bufferSize = ctx.sampleRate * 0.4;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
       data[i] = Math.random() * 2 - 1;
    }

    const noiseSou = ctx.createBufferSource();
    noiseSou.buffer = buffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = "bandpass";
    noiseFilter.frequency.setValueAtTime(400, now);
    noiseFilter.frequency.exponentialRampToValueAtTime(2500, now + 0.25);
    noiseFilter.Q.value = 3;

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.5, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.005, now + 0.35);

    noiseSou.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(ctx.destination);

    noiseSou.start(now + 0.05);
    noiseSou.stop(now + 0.4);
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}

export function playShootSFX() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // 白噪声爆炸
    const bufferSize = ctx.sampleRate * 1.5;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
       data[i] = Math.random() * 2 - 1;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(3200, now);
    filter.frequency.exponentialRampToValueAtTime(15, now + 1.2);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.7, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 1.4);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    source.start(now);
    source.stop(now + 1.5);

    // 初始金属触发"咔嗒"声与低沉子弹撞击声
    const click = ctx.createOscillator();
    click.type = "triangle";
    click.frequency.setValueAtTime(180, now);
    click.frequency.setValueAtTime(40, now + 0.08);

    const clickGain = ctx.createGain();
    clickGain.gain.setValueAtTime(0.6, now);
    clickGain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);

    click.connect(clickGain);
    clickGain.connect(ctx.destination);

    click.start(now);
    click.stop(now + 0.25);
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}

export function playVoteSFX() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // 谐振低音基础
    const fundamental = 120; // 120Hz deep dome bell
    const overtones = [1, 1.5, 2, 2.5, 3.2, 4.1];
    
    overtones.forEach((ratio, index) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(fundamental * ratio, now);

      const gain = ctx.createGain();
      // higher frequencies decay faster
      const peak = 0.15 / (index + 1);
      const duration = 3.0 / ratio;

      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(peak, now + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + duration + 0.2);
    });
  } catch {
    // Web Audio blocked by browser policy — silently ignored
  }
}
