from PIL import Image, ImageDraw, ImageFont
import math as m

# --- Config ---
ttf_path = "hud_lib/bahnschrift.ttf"
font_name = ttf_path.split("/")[-1].split(".")[0]
font_size = 96
byte_per_row = m.ceil(font_size / 8)
max_unicode = 127  # or higher if you want more characters
# -----------------

font = ImageFont.truetype(ttf_path, font_size)

# Initialize font array with all zeros
header_lines = []
header_lines.append(f"""#define FONT{font_size}_BYTES_PER_CHAR {font_size}*{byte_per_row}
#define FONT{font_size}_CHAR_COUNT {max_unicode}

const uint8_t font{font_size}_{font_name}[FONT{font_size}_CHAR_COUNT][FONT{font_size}_BYTES_PER_CHAR] = {{""")

for code in range(max_unicode):
    c = chr(code)

    # create blank 48x48 monochrome image
    img = Image.new("1", (font_size, font_size), 0)
    draw = ImageDraw.Draw(img)

    # center the glyph
    bbox = font.getbbox(c)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((font_size - w) // 2 - bbox[0], (font_size - h) // 2 - bbox[1]), c, font=font, fill=1)

    # convert to 6 bytes per row (font_size pixels per row)
    data_bytes = []
    for y in range(font_size):
        for bx in range(byte_per_row):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                pixel = img.getpixel((x, y))
                byte = (byte << 1) | pixel
            data_bytes.append(byte)

    # convert to hex for readability
    hex_bytes = ",".join(f"0x{b:02X}" for b in data_bytes)
    header_lines.append(f"  {{{hex_bytes}}},  // Unicode {code}")

header_lines.append("};")

# Save to .h file
with open(f"font{font_size}x{font_size}_{font_name}.h", "w") as f:
    f.write("\n".join(header_lines))