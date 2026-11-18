"""Composition and layout decisions shared by the cloud and local storytellers."""
LAYOUTS = ("auto", "narrator-top", "narrator-bottom", "narrator-left", "narrator-right")
OUTPUT_RATIO = "1080:1920"


def split_layout(selection, proposed=None):
    if selection != "auto":
        return selection
    return proposed if proposed in LAYOUTS[1:] else "narrator-top"


def compose_split(tool, ffmpeg, narrator, story, output, layout, seconds):
    horizontal = layout in ("narrator-left", "narrator-right")
    reverse = layout in ("narrator-bottom", "narrator-right")
    width, height = (540, 1920) if horizontal else (1080, 960)
    orientation = "hstack" if horizontal else "vstack"
    order = "[story][host]" if reverse else "[host][story]"
    filter_graph = (
        f"[0:v]fps=24,scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1[host];"
        f"[1:v]fps=24,scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1[story];"
        f"{order}{orientation}=inputs=2,"
        f"drawbox=x={'iw/2-2' if horizontal else '0'}:y={'0' if horizontal else 'ih/2-2'}:"
        f"w={'4' if horizontal else 'iw'}:h={'ih' if horizontal else '4'}:c=0x73CFC3:t=fill[composite]"
    )
    ffmpeg(tool, "-i", narrator, "-i", story, "-filter_complex_threads", "2",
           "-filter_complex", filter_graph, "-map", "[composite]", "-an",
           "-t", seconds, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-threads", "4", "-pix_fmt", "yuv420p", output)
