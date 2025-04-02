from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename

import os, io

import base64
from google import genai
from google.genai import types


#model = GenerativeModel("gemini-1.5-flash-001")

def generate(filename):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY")
    )
    prompt = """
    Please provide an exact trascript for the audio, followed by sentiment analysis.
pyth
    Your response should follow the format:

    Text: USERS SPEECH TRANSCRIPTION

    Sentiment Analysis: positive|neutral|negative

    
    Sentiment Score: Sentiment score

    Sentiment Magnitude: Sentiment Magnitude
    """
    myfile = client.files.upload(file=filename)

    with open(filename, 'rb') as f:
        audio_bytes = f.read()

    model = "gemini-2.0-flash"

    generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_mime_type ="text/plain",
    )

    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(
            data=audio_bytes,
            mime_type='audio/wav',
        )
        ],
        config = generate_content_config,
    )
    return response.text



#######
#######

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files():
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if allowed_file(filename):
            files.append(filename)
            print(filename)
    files.sort(reverse=True)
    return files



@app.route('/')
def index():
    files = get_files()
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        #filename = secure_filename(file.filename)
        filename =  datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        #
        #
        # Modify this block to call the speech to text API
        # Save transcript to same filename but .txt
        #
        #
        text = generate(file_path)
        
        f = open(file_path+'.txt','w')
        f.write(text)
        f.close()
        #

    return redirect('/') #success

@app.route('/upload/<filename>')
def get_file(filename):
    return send_file(filename)

 
@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
