import streamlit as st
import wave
import struct
import zlib
import io
import math
import pyotp
import qrcode
import time

# Secret key for OTP generation
SHARED_OTP_SEED = "JBSWY3DPEHPK3PXP" 


# --- ENCODING ENGINE ---
def generate_wave_and_encode(secret_bytes, file_label, otp_secret, tone_frequency=440.0):
    # Get current timestamp for expiration check
    creation_timestamp = int(time.time())
    
    # Generate the current 6-digit OTP code
    totp = pyotp.TOTP(otp_secret)
    active_code = totp.now()
    
    # Compress the input data to save space
    compressed_payload = zlib.compress(secret_bytes)
    payload_length = len(compressed_payload)
    
    # Pad filename to exactly 64 bytes so the header size is always predictable
    fixed_filename = file_label.ljust(64)[:64].encode('utf-8')
    otp_bytes = active_code.encode('utf-8')  # OTP is always 6 bytes
    
    # Header format: payload size (4B), timestamp (4B), OTP (6B), filename (64B). Total = 78 bytes
    header = struct.pack("<II6s64s", payload_length, creation_timestamp, otp_bytes, fixed_filename)
    
    final_payload = header + compressed_payload
    total_bits = len(final_payload) * 8

    # Audio configuration (using 44.1kHz mono)
    sample_rate = 44100
    num_channels = 1
    sampwidth = 2
    num_samples = total_bits
    
    center_offset = 32768
    max_amplitude = 15000 
    
    # Hide bits into the audio samples (LSB steganography)
    samples = []
    bit_index = 0
    for i in range(num_samples):
        time_sec = i / sample_rate
        base_sample = center_offset + (max_amplitude * math.sin(2 * math.pi * tone_frequency * time_sec))
        audio_integer = int(base_sample)
        
        byte_idx = bit_index // 8
        bit_pos = bit_index % 8
        target_byte = final_payload[byte_idx]
        bit_to_hide = (target_byte >> (7 - bit_pos)) & 1
        
        # Clear the last bit and insert our data bit
        modified_integer = (audio_integer & 0xFFFE) | bit_to_hide
        samples.append(modified_integer)
        bit_index += 1

    # Pack samples as unsigned short ('H') to prevent audio overflow clip bugs
    encoded_frames = struct.pack(f"<{num_samples}H", *samples)
    
    output_buffer = io.BytesIO()
    with wave.open(output_buffer, "wb") as wav_out:
        wav_out.setparams((num_channels, sampwidth, sample_rate, num_samples, 'NONE', 'not compressed'))
        wav_out.writeframes(encoded_frames)
        
    return output_buffer.getvalue(), (num_samples / sample_rate), active_code


# --- DECODING ENGINE ---
def decode_and_verify_audio(audio_bytes, otp_secret, user_entered_otp):
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_in:
        nframes = wav_in.getnframes()
        raw_frames = wav_in.readframes(nframes)
        
    num_samples = len(raw_frames) // 2
    samples = struct.unpack(f"<{num_samples}H", raw_frames)
    
    # Helper function to extract bytes out of the audio LSBs
    def extract_bytes(start_sample, num_bytes):
        extracted = bytearray()
        current_byte = 0
        bit_count = 0
        end_sample = start_sample + (num_bytes * 8)
        
        for i in range(start_sample, end_sample):
            bit = samples[i] & 1
            current_byte = (current_byte << 1) | bit
            bit_count += 1
            if bit_count == 8:
                extracted.append(current_byte)
                current_byte = 0
                bit_count = 0
        return bytes(extracted)

    try:
        # Extract and unpack the 78-byte header structure
        header_bytes = extract_bytes(0, 78)
        payload_length, creation_time, embedded_otp_bytes, fixed_filename_bytes = struct.unpack("<II6s64s", header_bytes)
        
        embedded_otp = embedded_otp_bytes.decode('utf-8')
        filename = fixed_filename_bytes.decode('utf-8').strip()
        
        # Expiration Check: check if more than 2 minutes (120 seconds) passed
        current_time = int(time.time())
        time_elapsed = current_time - creation_time
        
        if time_elapsed > 120:
            return None, None, f"❌ ACCESS DENIED: Security lifetime exceeded! This audio track expired {time_elapsed - 120} seconds ago. Generate a fresh signal."
            
        if time_elapsed < -5: 
            return None, None, "❌ ACCESS DENIED: Critical timestamp paradox detected. Sync system clocks."

        # Check if the user's OTP matches the one hidden in the audio file
        if user_entered_otp != embedded_otp:
            return None, None, "❌ ACCESS DENIED: Digital token signature mismatch! The code does not match this specific track file."
            
        # Verify if OTP is still valid within the current TOTP time window
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(user_entered_otp, valid_window=2):
            return None, None, "❌ ACCESS DENIED: Token authorization window expired!"
        
        # Extract payload bits, skip past the 78-byte header
        start_sample_payload = 78 * 8
        compressed_data = extract_bytes(start_sample_payload, payload_length)
        original_file_bytes = zlib.decompress(compressed_data)
        
        remaining_time = 120 - time_elapsed
        return original_file_bytes, filename, f"🔓 Access Authorized. (Decoded within deadline window: {remaining_time}s remaining)."
    except Exception as e:
        return None, None, f"❌ Extraction Failed. Audio track invalid or corrupted: {str(e)}"


# --- MAIN INTERFACE WORKSPACE ---
st.set_page_config(page_title="Unified Audio Signal Utility", layout="centered")
st.title("🛡️ Secure Signal Workspace (Unified)")
st.write("Synthesize data directly into expiring audio carriers or extract hidden assets via token authentication.")

tab1, tab2 = st.tabs(["🔒 Secure & Encode", "🔓 Authenticate & Decode"])

# --- TAB 1: ENCODER SYSTEM ---
with tab1:
    st.header("Generate Time-Locked Signal")
    input_mode = st.radio("Choose Input Payload Format:", ["Write a Text Message", "Upload a Dataset File"], key="mode_sel")

    payload_bytes = None
    label_name = ""

    if input_mode == "Write a Text Message":
        user_message = st.text_area("Type your secret text payload here:", key="txt_box")
        if user_message:
            payload_bytes = user_message.encode('utf-8')
            label_name = "secret_message.txt"
    else:
        uploaded_file = st.file_uploader("Upload target dataset file:", key="file_box")
        if uploaded_file:
            payload_bytes = uploaded_file.read()
            label_name = uploaded_file.name

    frequency_selection = st.slider("Select Carrier Base Frequency (Hz)", min_value=220, max_value=880, value=440, step=110, key="freq_slider")

    if payload_bytes is not None:
        if st.button("Synthesize Time-Locked Signal", key="generate_btn"):
            with st.spinner("Embedding strict timestamp matrix coordinates..."):
                generated_wav, duration, generated_otp = generate_wave_and_encode(
                    payload_bytes, label_name, SHARED_OTP_SEED, frequency_selection
                )
                
                st.success("🎉 Secure data tone successfully generated!")
                st.warning("⚠️ CRITICAL Lifespan: This track will expire automatically in exactly 2 minutes (120 seconds)!")
                
                col1, col2 = st.columns(2)
                col1.metric("Audio Duration", f"{duration:.2f} Sec")
                col2.metric("Active Dynamic OTP", f"{generated_otp}")
                
                st.audio(generated_wav, format="audio/wav")
                
                # QR setup for streaming tokens easily
                qr_data = f"SIGNAL_AUTH://OTP:{generated_otp}//LIFESPAN:120s"
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(qr_data)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                img_buf = io.BytesIO()
                qr_img.save(img_buf, format="PNG")
                
                st.subheader("📋 Synchronized Gateway Context QR")
                st.image(img_buf.getvalue(), caption="Scan code to transfer verification tracking variables.")
                
                st.download_button(
                    label="📥 Download Synthesized WAV Carrier",
                    data=generated_wav,
                    file_name="time_locked_signal.wav",
                    mime="audio/wav",
                    key="dl_btn"
                )

# --- TAB 2: DECODER SYSTEM ---
with tab2:
    st.header("Decode Data Signal Matrix")
    carrier_audio = st.file_uploader("Upload Received WAV Audio Carrier File:", type=["wav"], key="upload_dec")
    user_otp = st.text_input("Enter Active 6-Digit Verification Token Code:", max_chars=6, type="password", key="otp_dec")

    if carrier_audio and user_otp:
        if st.button("Unseal Data Payload", key="decode_btn"):
            if len(user_otp) != 6 or not user_otp.isdigit():
                st.error("Authentication Token format must be exactly 6 digits long.")
            else:
                with st.spinner("Calculating track lifespan age matrix..."):
                    audio_stream = carrier_audio.read()
                    extracted_bytes, name_of_file, log_msg = decode_and_verify_audio(audio_stream, SHARED_OTP_SEED, user_otp)
                    
                    if extracted_bytes:
                        st.success(log_msg)
                        
                        if name_of_file == "secret_message.txt":
                            st.text_area("Unsealed Plaintext Preview:", value=extracted_bytes.decode('utf-8'), height=150, key="preview_box")
                            
                        st.download_button(
                            label=f"📥 Download Extracted Asset ({name_of_file})",
                            data=extracted_bytes,
                            file_name=name_of_file,
                            mime="application/octet-stream",
                            key="save_asset_btn"
                        )
                    else:
                        st.error(log_msg)