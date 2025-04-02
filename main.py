from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename

import os, io

from google.cloud import speech
from google.protobuf import wrappers_pb2
from google.cloud import texttospeech_v1
from IPython.display import Audio, display
from google.cloud import language_v2

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

def sample_analyze_sentiment(text_content: str = "The weather is nice."):
    """
    Analyzes Sentiment in a string.

    Args:
      text_content: The text content to analyze.
    """

    client = language_v2.LanguageServiceClient()

    # text_content = 'I am so happy and joyful.'

    # Available types: PLAIN_TEXT, HTML
    document_type_in_plain_text = language_v2.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    language_code = "en"
    document = {
        "content": text_content,
        "type_": document_type_in_plain_text,
        "language_code": language_code,
    }

    # Available values: NONE, UTF8, UTF16, UTF32
    # See https://cloud.google.com/natural-language/docs/reference/rest/v2/EncodingType.
    encoding_type = language_v2.EncodingType.UTF8

    response = client.analyze_sentiment(
        request={"document": document, "encoding_type": encoding_type}
    )
    # Get overall sentiment of the input document
    print(f"Document sentiment score: {response.document_sentiment.score}")
    print(f"Document sentiment magnitude: {response.document_sentiment.magnitude}")
    # Get sentiment for all sentences in the document
    for sentence in response.sentences:
        print(f"Sentence text: {sentence.text.content}")
        print(f"Sentence sentiment score: {sentence.sentiment.score}")
        print(f"Sentence sentiment magnitude: {sentence.sentiment.magnitude}")

    # Get the language of the text, which will be the same as
    # the language specified in the request or, if not specified,
    # the automatically-detected language.
    print(f"Language of the text: {response.language_code}")

    return response

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

        client=speech.SpeechClient()

        with io.open(file_path, "rb") as audio_file:
            content = audio_file.read()
        audio=speech.RecognitionAudio(content=content)

        config=speech.RecognitionConfig(
        #encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        #sample_rate_hertz=44100,
            language_code="en-US",
            model="default",
            audio_channel_count=1,
            enable_word_confidence=True,
            enable_word_time_offsets=True,
        )

        # Detects speech in the audio file
        operation=client.long_running_recognize(config=config, audio=audio)

        #print("Waiting for operation to complete...")
        response=operation.result(timeout=90)

        txt = ''
        for result in response.results:
            txt = txt + result.alternatives[0].transcript + '\n'

        text = txt
        #f = open('uploads/'+filename+'score' +'.txt','w')
        #f.write(txt)
        #f.close()

        sentiment = sample_analyze_sentiment(str(text))
        score = sentiment.document_sentiment.score * sentiment.document_sentiment.magnitude
        text = text + "Document Score:" + str(sentiment.document_sentiment.score) + '\n'
        text = text + "Document Magnitude:" + str(sentiment.document_sentiment.magnitude) + '\n'
        if score > 0.75:
            text = text + "Sentiment - POSITIVE" + '\n' 
        elif score < -0.75:
            text = text + "Sentiment - NEGATIVE" + '\n'
        else:
            text = text + "Sentiment - NEUTRAL"+ '\n'
        

        f = open('uploads/'+filename +'.txt','w')
        f.write(text)

        f.close()
        #

    return redirect('/') #success

@app.route('/upload/<filename>')
def get_file(filename):
    return send_file(filename)

    
@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)
    #
    #
    # Modify this block to call the stext to speech API
    # Save the output as a audio file in the 'tts' directory 
    # Display the audio files at the bottom and allow the user to listen to them
    #
    client = texttospeech_v1.TextToSpeechClient()
    input = texttospeech_v1.SynthesisInput()
    input.text = text   
    voice = texttospeech_v1.VoiceSelectionParams()
    voice.language_code = "en-US"
    # voice.ssml_gender = "MALE"

    audio_config = texttospeech_v1.AudioConfig()
    audio_config.audio_encoding = "LINEAR16"

    req = texttospeech_v1.SynthesizeSpeechRequest(
    input=input,
    voice=voice,
    audio_config=audio_config,
    )

    response = client.synthesize_speech(request=req)
                                        
    wav = response.audio_content

    # save audio
    filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    f = open('uploads/'+filename,'wb')
    f.write(wav)
    f.close()

    sentiment = sample_analyze_sentiment(text)
    score = sentiment.document_sentiment.score * sentiment.document_sentiment.magnitude
    text = text + '\n' + "Document Score:" + str(sentiment.document_sentiment.score) + '\n'
    text = text + "Document Magnitude:" + str(sentiment.document_sentiment.magnitude) + '\n'
    if score > 0.75:
        text = text + "Sentiment - POSITIVE" + '\n' 
    elif score < -0.75:
        text = text + "Sentiment - NEGATIVE" + '\n'
    else:
        text = text + "Sentiment - NEUTRAL"+ '\n'

    #save text
    f = open('uploads/'+filename + '.txt','w')
    f.write(text)
    f.close()
    #

    return redirect('/') #success

@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)