from flask import Flask, render_template, request, jsonify, send_from_directory
import google.generativeai as genai
import os
import textwrap
import json
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import uuid
def compress_for_ai(image, max_size=(800, 800)):
    """AI ko bhejne se pehle image ko chhota aur fast banata hai"""
    img_copy = image.copy()
    img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img_copy

# Setup Flask App
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['ASSETS_FOLDER'] = 'assets'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# 🧠 The "AI Director" God Prompt (Funny mood, perfect spelling)
ai_director_prompt = """
You are a dual-threat AI: A toxic but FUNNY BGMI Coach AND an Expert Graphic Designer.
I am sending you images. 
- The FIRST image(s) are the user's BGMI screenshots.
- The LAST image is the Background Template.

TASK 1 (The Roast): Generate a brutal, savage, but FUNNY Samay Raina style Hinglish roast (under 40 words). Attack their skins vs actual skills. CRITICAL: Ensure ZERO spelling mistakes in Hinglish.
TASK 2 (The Layout): Analyze the Background Template. Find the best empty space (Top, Center, or Bottom). Decide the best text color (white or black) for readability.

Output ONLY a raw JSON object:
{
  "roast_text": "Your funny Hinglish roast here...",
  "layout": {
    "vertical_position": "top", 
    "text_color": "white",
    "stroke_color": "black"
  }
}
Note: 'vertical_position' must be 'top', 'center', or 'bottom'.
"""

# 🛠️ Image Compositing Function
def create_final_image(roast_text, layout_data, base_image_path, font_path):
    try:
        base_img = Image.open(base_image_path).convert("RGBA")
        txt_img = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(txt_img)
        
        try:
            font_size = int(base_img.width * 0.06)
            fnt = ImageFont.truetype(font_path, font_size)
            wm_fnt = ImageFont.truetype(font_path, int(base_img.width * 0.035))
        except IOError:
            fnt = ImageFont.load_default()
            wm_fnt = ImageFont.load_default()
            
        fill_color = (255, 255, 255, 255) if layout_data.get("text_color", "white").lower() == "white" else (0, 0, 0, 255)
        stroke_color = (0, 0, 0, 230) if layout_data.get("stroke_color", "black").lower() == "black" else (255, 255, 255, 230)
            
        wrapper = textwrap.TextWrapper(width=28)
        word_list = wrapper.wrap(text=roast_text)
        caption_new = '\n'.join(word_list)
        
        bbox = d.multiline_textbbox((0, 0), caption_new, font=fnt, spacing=15)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x_center = (base_img.width - text_w) / 2
        
        ai_position = layout_data.get("vertical_position", "center").lower()
        if ai_position == "top":
            y_center = base_img.height * 0.15
        elif ai_position == "bottom":
            y_center = base_img.height * 0.70
        else:
            y_center = (base_img.height - text_h) / 2
        
        d.multiline_text((x_center, y_center), caption_new, font=fnt, fill=fill_color, align="center", spacing=15, stroke_width=4, stroke_fill=stroke_color)
        
        # Text Watermark (Top Right Corner)
        watermark_text = "@ToxicCoach.AI"
        wm_bbox = d.textbbox((0, 0), watermark_text, font=wm_fnt)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_x = base_img.width - wm_w - 30
        wm_y = 30 # Sabse upper corner
        
        d.text((wm_x, wm_y), watermark_text, font=wm_fnt, fill=(255, 255, 255, 180), stroke_width=2, stroke_fill=(0,0,0,180))
            
        final_out = Image.alpha_composite(base_img, txt_img).convert("RGB")
        
        output_filename = f"roasted_{uuid.uuid4().hex}.jpg"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        final_out.save(output_path, quality=95)
        return output_filename
        
    except Exception as e:
        print(f"Image Error: {e}")
        return None

# Routes
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/roast', methods=['POST'])
def roast():
    if 'files[]' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    files = request.files.getlist('files[]')
    if len(files) == 0 or files[0].filename == '':
        return jsonify({"error": "Bhai, kam se kam ek screenshot toh upload kar!"}), 400
    if len(files) > 3:
        return jsonify({"error": "Jyada shana mat ban! Max 3 files allowed hain."}), 400

    saved_images = []
    for file in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        saved_images.append(Image.open(filepath))

    # Random Background Selection from assets
    possible_templates = [f for f in os.listdir(app.config['ASSETS_FOLDER']) if f.startswith('bgmi_template') and f.endswith(('.png', '.jpg'))]
    if not possible_templates:
        return jsonify({"error": "Background templates missing in assets folder!"}), 500
        
    selected_bg_name = random.choice(possible_templates)
    selected_bg_path = os.path.join(app.config['ASSETS_FOLDER'], selected_bg_name)
    font_path = os.path.join(app.config['ASSETS_FOLDER'], "gaming_font.ttf")

    try:
        payload = [ai_director_prompt]
        
        # NAYA FAST CODE: User ki images compress karke payload mein daalo
        for img in saved_images:
            payload.append(compress_for_ai(img))
            
        # Background template ko bhi compress karke daalo
        bg_img = Image.open(selected_bg_path)
        payload.append(compress_for_ai(bg_img))
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(payload)
        
        raw_response = response.text.strip()
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:-3]
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:-3]
            
        ai_data = json.loads(raw_response)
        
        final_img_name = create_final_image(ai_data.get("roast_text", ""), ai_data.get("layout", {}), selected_bg_path, font_path)
        
        if final_img_name:
            return jsonify({"success": True, "image_url": f"/outputs/{final_img_name}"})
        else:
            return jsonify({"error": "Image composition failed."}), 500

    except Exception as e:
        print(e)
        return jsonify({"error": "AI Processing failed. Try again."}), 500

@app.route('/outputs/<filename>')
def serve_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)