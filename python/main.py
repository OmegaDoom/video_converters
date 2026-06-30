import av
import time  # Built-in library to track execution duration

# 1. Open the .nut container
container = av.open("noise.nut")
output_container = av.open("decoded_output.mp4", mode="w")

print("--- Container Stream Information ---")
for stream in container.streams:
    print(f"Index: {stream.index} | Type: {stream.type} | Codec: {stream.codec_context.name}")

# 2. Separate streams for targeting
video_stream = container.streams.video[0]
audio_stream = container.streams.audio[0]

# 1. Read Resolution
width = video_stream.width
height = video_stream.height

print(f"Resolution: {width}x{height}")

out_video = output_container.add_stream("h264", rate=video_stream.average_rate or 30)
out_video.width = width
out_video.height = height
out_video.pix_fmt = "yuv420p"  # Standard color space for regular media players
out_video.color_range = av.video.reformatter.ColorRange.JPEG  # Keep full 0-255

out_audio = output_container.add_stream("aac", rate=audio_stream.rate)
out_audio.layout = audio_stream.layout

# Track loop statistics
frame_count = 0

print("\nProcessing streams... Please wait.")
# ────────────────────────────────────────────────────────
# START THE BENCHMARK TIMER
# ────────────────────────────────────────────────────────
start_time = time.perf_counter()

# 3. Demux first, check stream type, then explicitly decode
for packet in container.demux():
# EXPLICIT VIDEO PATH
    if packet.stream.type == "video":
        for frame in packet.decode():
            frame_count += 1
            plane = frame.planes[0]
            # 1. Get the read-only memory buffer from Plane 0 (RGBA is packed in Plane 0)
            # We use a memoryview to safely read the bytes out of RAM
            read_only_buffer = memoryview(frame.planes[0])

            # 2. Copy the bytes into a mutable (changeable) Python bytearray
            mutable_bytes = bytearray(read_only_buffer)

            # 3. MODIFY YOUR BYTES HERE
            for i in range(0, len(mutable_bytes) // 4, 2):
                mutable_bytes[4 * i] = 255
                mutable_bytes[4 * i + 1] = 0
                mutable_bytes[4 * i + 2] = 0
                mutable_bytes[4 * i + 3] = 255

            # 4. Create a completely new blank frame with matching dimensions
            new_frame = av.VideoFrame(width=width, height=height, format="rgba")

            # 5. Write your modified bytearray back into the new frame's plane memory
            new_frame.planes[0].update(mutable_bytes)
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            for out_packet in out_video.encode(new_frame):
                output_container.mux(out_packet)

            # EXPLICIT AUDIO PATH
    elif packet.stream.type == "audio":
        for frame in packet.decode():
            frame.pts = frame.pts
            frame.time_base = frame.time_base
            for out_packet in out_audio.encode(frame):
                output_container.mux(out_packet)

for out_packet in out_video.encode():
    output_container.mux(out_packet)

for out_packet in out_audio.encode():
    output_container.mux(out_packet)

output_container.close()
container.close()

# ────────────────────────────────────────────────────────
# END THE BENCHMARK TIMER & PRINT STATS
# ────────────────────────────────────────────────────────
end_time = time.perf_counter()
total_duration = end_time - start_time

print("\n================ BENCHMARK RESULTS ================")
print(f"Total Processing Time : {total_duration:.4f} seconds")
print(f"Total Video Frames    : {frame_count} frames")
if total_duration > 0:
    print(f"Processing Speed      : {frame_count / total_duration:.2f} FPS")
print("===================================================")