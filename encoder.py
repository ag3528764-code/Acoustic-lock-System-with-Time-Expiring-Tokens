import streamlit as st
import wave
import struct
import zlib
import io
import math
import pyotp
import qrcode
import time

def generate_wave_and_encode(secret_bytes, file_label, otp_secret, tone_frequency=440.0):
    # Save the time when the file is generated
    creation_timestamp = int(time.time())
    
    # Get current 6 digit OTP token
    totp = pyotp.TOTP(otp_secret)
    active_code = totp.now()
    
    # Compress input payload using zlib
    compressed_payload = zlib.compress(secret_bytes)
    payload_length = len(compressed_payload)
    
    # Make filename exactly 64 characters so struct unpack sizes match up
    fixed_filename = file_label.ljust(64)[:64].encode('utf-8')
    otp_bytes = active_code.encode('utf-8')  # Always 6 bytes
    
    # Build fixed size 78-byte header: payload size, timestamp, otp, filename
    header = struct.pack("<II6s64s", payload_length, creation_timestamp, otp_bytes, fixed_filename)
    
    final_payload = header + compressed_payload
    total_bits = len(final_payload) * 8

    # Audio synthesis variables setup
    sample_rate = 44100
    num_samples = total_bits
    samples = []
    
    center_offset = 32768
    max_amplitude = 15000 
    
    # Loop over bits to embed them into audio track samples (LSB manipulation)
    bit_index = 0
    for i in range(num_samples):
        time_sec = i / sample_rate
        base_sample = center_offset + (max_amplitude * math.sin(2 * math.pi * tone_frequency * time_sec))
        audio_integer = int(base_sample)
        
        byte_idx = bit_index // 8
        bit_pos = bit_index % 8
        target_byte = final_payload[byte_idx]
        bit_to_hide = (target_byte >> (7 - bit_pos)) & 1
        
        # Replace the original last bit with the raw data bit
        modified_integer = (audio_integer & 0xFFFE) | bit_to_hide
        samples.append(modified_integer)
        bit_index += 1

    # Pack samples as unsigned 16-bit short integers ('H') to stop any clipping bugs
    encoded_frames = struct.pack(f"<{num_samples}H", *samples)
    
    output_buffer = io.BytesIO()
    with wave.open(output_buffer, "wb") as wav_out:
        wav_out.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
        wav_out.writeframes(encoded_frames)
        
    return output_buffer.getvalue(), (num_samples / sample_rate), active_code

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Secure Data Encoder", layout="centered")
st.title("🔒 2-Minute Expiry Signal Synthesizer (Encoder)")
st.write("Synthesize data into a standalone wave track that expires exactly 120 seconds after creation.")

# Shared secret key for matching OTP values
SHARED_OTP_SEED = "JBSWY3DPEHPK3PXP" 

input_mode = st.radio("Choose Input Payload Format:", ["Write a Text Message", "Upload a Dataset File"])

payload_bytes = None
label_name = ""

if input_mode == "Write a Text Message":
    user_message = st.text_area("Type your secret text payload here:")
    if user_message:
        payload_bytes = user_message.encode('utf-8')
        label_name = "secret_message.txt"
else:
    uploaded_file = st.file_uploader("Upload target dataset file:")
    if uploaded_file:
        payload_bytes = uploaded_file.read()
        label_name = uploaded_file.name

frequency_selection = st.slider("Select Carrier Base Frequency (Hz)", min_value=220, max_value=880, value=440, step=110)

if payload_bytes is not None:
    if st.button("Synthesize Time-Locked Signal"):
        with st.spinner("Embedding strict timestamp matrix coordinates..."):
            generated_wav, duration, generated_otp = generate_wave_and_encode(
                payload_bytes, label_name, SHARED_OTP_SEED, frequency_selection
            )
            
            st.success("🎉 Secure data tone successfully generated!")
            st.warning("⚠️ CRITICAL SECURITY WARNING: This file will automatically expire and become invalid in exactly 2 minutes (120 seconds)!")
            
            col1, col2 = st.columns(2)
            col1.metric("Generated Audio Length", f"{duration:.2f} Sec")
            col2.metric("Active Dynamic OTP", f"{generated_otp}")
            
            st.audio(generated_wav, format="audio/wav")
            
            # Generate QR code for mobile scanner lookup compatibility
            qr_data = f"SIGNAL_AUTH://OTP:{generated_otp}//LIFESPAN:120s"
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr_data_str = qr_data
            qr.add_data(qr_data_str)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            img_buf = io.BytesIO()
            qr_img.save(img_buf, format="PNG")
            
            st.subheader("📋 Synchronized Gateway Context QR")
            st.image(img_buf.getvalue(), caption="Scan code to view verification parameters.")
            
            st.download_button(
                label="📥 Download Synthesized WAV Carrier",
                data=generated_wav,
                file_name="time_locked_signal.wav",
                mime="audio/wav"
            )