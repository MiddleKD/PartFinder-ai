from PIL import Image, ImageSequence

def get_gif_fps(gif_path):
    gif = Image.open(gif_path)
    durations = [frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
    avg_duration = sum(durations) / len(durations)
    fps = 1000 / avg_duration  # duration is in milliseconds
    return fps

def optimize_gif(input_gif_path, output_gif_path, resize_factor=1.0, frame_skip=1, start_frame=0, end_frame=None):
    # Open the input GIF file
    original_gif = Image.open(input_gif_path)
    
    # Get all frames from the original GIF
    frames = [frame.copy() for frame in ImageSequence.Iterator(original_gif)]
    
    # Apply frame skipping and cropping
    frames = frames[start_frame:end_frame:frame_skip]
    
    # Resize frames if resize_factor is specified
    if resize_factor != 1.0:
        frames = [
            frame.resize(
                (int(frame.width * resize_factor), int(frame.height * resize_factor)), 
                Image.ANTIALIAS
            ) 
            for frame in frames
        ]
    
    # Get duration for each frame and adjust according to frame_skip
    durations = [frame.info['duration'] for frame in ImageSequence.Iterator(original_gif)]
    durations = durations[start_frame:end_frame:frame_skip]
    
    # Save the optimized GIF
    frames[0].save(
        output_gif_path, 
        save_all=True, 
        append_images=frames[1:], 
        optimize=True, 
        loop=0,
        duration=durations
    )

# Example usage
input_gif = "p4.gif"
output_gif = "output.gif"
resize_factor = 0.5  # Resize to 50% of the original size
frame_skip = 10       # Skip every 2 frames
start_frame = 0      # Start at the first frame
end_frame = -1       # End at the 30th frame

# Get the FPS of the original GIF
fps = get_gif_fps(input_gif)
print(f"Original GIF FPS: {fps}")

optimize_gif(input_gif, output_gif, resize_factor, frame_skip, start_frame, end_frame)
