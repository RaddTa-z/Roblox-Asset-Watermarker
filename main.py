from flask import Flask, jsonify, request, send_file
import time
import requests
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageColor, ImageFilter
from io import BytesIO

app = Flask(__name__)

ROBLOX_API_URL = "https://thumbnails.roblox.com/v1/assets"

def get_asset_name(asset_id):
    asset_info_url = f"https://economy.roproxy.com/v2/assets/{asset_id}/details"
    response = requests.get(asset_info_url)
    data = response.json()
    try:
        return data["Name"]
    except KeyError:
        return "Name Not Found"

def add_watermark(original_img_url, watermark_img_url, opacity=1.0, text=None, text_color="white", outline_color="black", font_size=25, outline_opacity=0.80, blur_radius=2):
    response = requests.get(original_img_url)
    original_img = Image.open(BytesIO(response.content))

    response = requests.get(watermark_img_url)
    watermark_img = Image.open(BytesIO(response.content)).convert("RGBA")

    if opacity < 1.0:
        alpha = watermark_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        watermark_img.putalpha(alpha)

    combined_img = Image.new("RGBA", (original_img.width, original_img.height), (0, 0, 0, 0))

    combined_img.paste(original_img, (0, 0))
    combined_img.paste(watermark_img, (0, 0), mask=watermark_img)

    if text:
        draw = ImageDraw.Draw(combined_img)

        if len(text) > 29:
            font_size = int(font_size * 0.8)

        font_file = "Mayberry_W02_Extrabold.ttf"
        font = ImageFont.truetype(font_file, size=font_size)

        text_width, text_height = draw.textsize(text, font=font)
        position = (10, combined_img.height - text_height - 10)

        # Draw the outline
        temp_img = Image.new('RGBA', combined_img.size, (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)

        for x in range(-blur_radius, blur_radius + 1):
            for y in range(-blur_radius, blur_radius + 1):
                temp_draw.text((position[0] + x, position[1] + y), text, font=font, fill=outline_color)

        if outline_opacity < 1.0:
            temp_alpha = temp_img.split()[3]
            temp_alpha = ImageEnhance.Brightness(temp_alpha).enhance(outline_opacity)
            temp_img.putalpha(temp_alpha)

        temp_img = temp_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        combined_img.alpha_composite(temp_img)

        # Draw the text
        draw.text(position, text, font=font, fill=text_color)

    png_image = combined_img.convert("RGBA")  # Change to RGBA for transparency

    return png_image

@app.route("/get_image", methods=["GET"])
def get_image_url():
    asset_ids_str = request.args.get("asset_id", None)
    if asset_ids_str is None:
        return "Please provide an asset ID.", 400

    asset_ids = asset_ids_str.split(',')

    params = {
        "assetIds": ','.join(asset_ids),
        "size": "420x420",
        "format": "Png",
    }

    response = requests.get(ROBLOX_API_URL, params=params)
    data = response.json()["data"]

    images = {}
    for asset_data in data:
        asset_id = str(asset_data["targetId"])
        original_img_url = asset_data["imageUrl"]
        watermark_img_url = "https://replicate.delivery/pbxt/Kg49TFp87m1YtQLdSYzOmGvQcHUtC31m4MYawczHZ6bggFJJ/download%20(1).jpg"
        
        while True:
            asset_name = get_asset_name(asset_id)
            if asset_name != "Name Not Found":
                break
            # Retry after a short delay
            time.sleep(1)
        
        opacity = float(request.args.get("opacity", 1.0))
        watermarked_img = add_watermark(original_img_url, watermark_img_url, opacity, text=asset_name)
        images[asset_id] = watermarked_img

    gridsize = int(request.args.get("gridsize", 2))

    combined_image = Image.new("RGBA", (420 * gridsize, 420 * ((len(images) + gridsize - 1) // gridsize)), (0, 0, 0, 0))  # Set transparent background
    for i, asset_id in enumerate(images):
        x = (i % gridsize) * 420
        y = (i // gridsize) * 420
        combined_image.paste(images[asset_id], (x, y))

    buffer = BytesIO()
    combined_image.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
