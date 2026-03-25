from PIL import Image, ImageDraw, ImageFont

# --- Config ---
ttf_path = "hud_lib/bahnschrift.ttf"
font_size = 48
max_unicode = 127  # or higher if you want more characters
# -----------------

font = ImageFont.truetype(ttf_path, font_size)

# Initialize font array with all zeros
header_lines = []
header_lines.append(f"""#define FONT48_BYTES_PER_CHAR 48*6
#define FONT48_CHAR_COUNT {max_unicode}

const uint8_t font48_digits[FONT48_CHAR_COUNT][FONT48_BYTES_PER_CHAR] = {{""")

for code in range(max_unicode):
    c = chr(code)

    # create blank 48x48 monochrome image
    img = Image.new("1", (48, 48), 0)
    draw = ImageDraw.Draw(img)

    # center the glyph
    bbox = font.getbbox(c)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((48 - w) // 2 - bbox[0], (48 - h) // 2 - bbox[1]), c, font=font, fill=1)

    # convert to 6 bytes per row (48 pixels per row)
    data_bytes = []
    for y in range(48):
        for bx in range(6):
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
with open("font48x48.h", "w") as f:
    f.write("\n".join(header_lines))