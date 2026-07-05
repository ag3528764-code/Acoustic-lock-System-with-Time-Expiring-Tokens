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
