# Acoustic-lock-System-with-Time-Expiring-Tokens
----------------------------------------------------------------------------------------------------------------------------------------------------------

This is a security project built with Python and Streamlit that uses sound waves to securely pass data. It hides compressed files or text inside a synthesized audio carrier wave using Least Significant Bit (LSB) steganography. To make it secure, it uses a Time-Based One-Time Password (TOTP) token system so that any generated audio file automatically expires and becomes invalid after exactly 2 minutes.

-------> The repo has two versions: a combined app with both features and a standalone encoder script.

 #  What it Does
 
--> LSB Audio Steganography: Injects text or raw files directly into the lowest bits of a 16-bit audio wave without ruining the sound.

--> 2-Minute Expiration Gate: Checks a custom 78-byte binary header for a Unix timestamp to calculate the file's age, and pairs it with the pyotp library to verify the token.

--> On-the-Fly Compression: Uses zlib to shrink the files before embedding them, which keeps the output audio track as short as possible.

--> Quick QR Generation: Automatically spits out a QR code when you generate the wave so you can easily view or share the token and tracking details.

--> Memory Efficient: Processes everything in RAM using byte streams (io.BytesIO), meaning it doesn't clutter your local drive with temp files.

#   Project Structure

encoderdecoderintegrated.py — The main integrated app. It has a two-tab dashboard layout so you can encode or decode from the same UI.

encoder.py — A standalone script that only handles the encoding and wave synthesis side of things.


#   Audio Settings

--> Sample Rate: 44.1 kHz (Standard CD quality, mono channel).

--> Quantization Space: Unsigned 16-bit short integers (<H). The wave shifts around a center point of 32,768 with a max amplitude of 15,000. This buffer prevents the math from clipping or throwing integer overflow bugs during bit swapping.

--> Bit Mixing: The loop modifies exactly 1 bit per audio sample, storing data directly into the least significant bit (LSB).

#   Security Workflow

--> Input: You type a message or upload a file, then choose a base frequency (like 440 Hz).

--> Packing: The script gets the current time, generates a live OTP code using the shared seed, builds the 78-byte header structure, and tacks on the compressed asset data.

--> Synthesis: It converts the whole bitstream into a .wav file that plays a tone holding the hidden data.

--> Decoding & Verification: The decoder reads the first 78 bytes to unpack the metadata. It subtracts the creation timestamp from the current system time. If the file is older than 120 seconds, or if the user's manual OTP token doesn't match the one hidden inside the wave, the gate locks and denies the download.
