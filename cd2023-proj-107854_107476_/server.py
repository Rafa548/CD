from flask import Flask, request, jsonify, render_template
from mutagen.mp3 import MP3
from io import BytesIO
from pydub import AudioSegment
from flask import Flask, send_file
from concurrent.futures import ThreadPoolExecutor
from flask import redirect
import pika
import os
import io
import wave

app = Flask(__name__)

executor = ThreadPoolExecutor()
music_data = []
music_files = {}
jobs = []
jobs_inicialize = []
job_id_counter = 1
music_id_counter = 1


class Music:
    def __init__(self, music_id, name, band, instrument_tracks,n_pieces):
        self.music_id = music_id
        self.name = name
        self.band = band
        self.n_pieces = n_pieces
        self.instrument_tracks = instrument_tracks
        self.processed = False
        self.processing_progress = 0

class Job:
    def __init__(self, job_id, music_id, size, time, track, link):
        self.job_id = job_id
        self.music_id = music_id
        self.size = size
        self.time = time
        self.track = track
        self.link = link

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['GET'])
def start():
    return render_template('start.html')

@app.route('/music', methods=['POST','GET'])
def submit_music():
    if request.method == 'POST':
        global music_id_counter
        global music_data
        global music_files
        global jobs_inicialize
        global jobs

        music_file = request.files['musicFile']
        octet_stream = BytesIO(music_file.read())

        audio = MP3(octet_stream)

        if 'TIT2' in audio:
            title = audio['TIT2'].text[0]
        else:
            title = 'Unknown Title'

        if 'TPE1' in audio:
            artist = audio['TPE1'].text[0]
        else:
            artist = 'Unknown Artist'

        music_id = music_id_counter
        selected_instruments = request.form.getlist('instrumentTrack')

        instrument_tracks = []
        for i, instrument in enumerate(selected_instruments):
            track = {
                'name': instrument,
                'track_id': i + 1
            }
            instrument_tracks.append(track)

        music_id_counter += 1

        file_name = f'{music_id}.mp3'
        save_path = os.path.join('Input', file_name)

        music_files[music_id] = octet_stream.getvalue()

        audio_data = BytesIO(music_files[music_id])
        audio = AudioSegment.from_file(audio_data, format="mp3")
        audio.export(save_path, format="mp3")

        #added ----------------------------------
        duration = len(audio)/1000
        n_pieces = int(duration/15)+1
        #----------------------------------------

        music = Music(music_id, title, artist, instrument_tracks,n_pieces)
        
        music_data.append(music)
        

        response = {
            'music_id': music_id,
            'name': title,
            'band': artist,
            'instrument_tracks': instrument_tracks
        }
        return redirect('/music')
    else:
        response = []
        for music in music_data:
            response.append({
                'music_id': music.music_id,
                'name': music.name,
                'band': music.band,
                'instrument_tracks': music.instrument_tracks
            })
        return render_template('allmusic.html', music_data=response)


@app.route('/music/<int:music_id>', methods=['POST','GET'])
def process_music(music_id):
    if request.method == 'POST':
        global music_data
        global job_id_counter
        for music in music_data:
            if music.music_id == music_id:
                if music.processed:
                    merged_audio = None
                    for track in music.instrument_tracks:
                        if track["name"] == 'Vocals':
                            audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Vocals_{music.music_id}.mp3')
                            print(" [x]  Got Vocals")
                        if track["name"] == 'Other':
                            audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Other_{music.music_id}.mp3')
                            print(" [x]  Got Other")
                        if track["name"] == 'Bass':
                            audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Bass_{music.music_id}.mp3')
                            print(" [x]  Got Bass")
                        if track["name"] == 'Drums':
                            audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Drums_{music.music_id}.mp3')
                            print(" [x]  Got Drums")
                        if merged_audio is None:
                            merged_audio = audio_segment
                        else:
                            merged_audio = merged_audio.overlay(audio_segment, position=0)
                    merged_audio.export(f'CompleteAudio/merged_{music.music_id}.mp3', format='mp3')    
                    print(" [x] Done Merging")
                    return redirect('/music/' + str(music_id))
                if music.processing_progress == 0:
                    print(" [x]  Starting Processing")
                    if music_id in music_files:
                        binary_audio = music_files[music_id]
                        audio_data = BytesIO(binary_audio)
                        #pieces = split_music(audio_data, 8)
                        pieces = split_music(audio_data, music.n_pieces)
                        for piece in pieces:
                            message_header = {'music_id': music_id,
                                            'piece_id': piece['id'],
                                            'selected_instruments': music.instrument_tracks,
                                            'job_id': job_id_counter}
                            jobs_inicialize.append(job_id_counter)
                            job_id_counter += 1
                            send_message(piece['data'],message_header) 
                        music.processed = False
                        music.processing_progress += 0.00000001
                        return redirect('/music/' + str(music_id))
                else:
                    return redirect('/music/' + str(music_id))
        return jsonify({'error': 'Music not found'}), 404
    else:
        for music in music_data:
            if music.music_id == music_id:
                instrument_urls = []
                if music.processed:
                    response = {
                        'status': 'processed',
                        'mix_file_url': f'/audio/merged_{music_id}.mp3',
                        'mix_file_name': f'merged_{music_id}.mp3'
                    }
                    instrument_tracks = music.instrument_tracks
                    for track in instrument_tracks:
                        instrument_urls.append({
                            'instrument': track['name'],
                            'url': f'/audio/{track["name"]}_{music_id}.mp3',
                            'name': f'{track["name"]}_{music_id}.mp3'
                        })
                else:
                    if music.processing_progress  < 1:
                        response = {
                        'status': 'processing',
                        'progress': 0
                    }
                    else:
                        response = {
                            'status': 'processing',
                            'progress': music.processing_progress
                        }
                return render_template('music.html', music=response, instrument_urls=instrument_urls)
        return render_template('music.html', music=None, instrument_urls=[])


@app.route('/music/edit/<int:music_id>', methods=['POST'])
def edit_music(music_id):
    selected_instruments = request.form.getlist(f'instrumentTrack_{music_id}[]')
    
    for music in music_data:
        if music.music_id == music_id:
            music.instrument_tracks = []
            for i, instrument in enumerate(selected_instruments):
                track = {
                    'name': instrument,
                    'track_id': i + 1
                }
                music.instrument_tracks.append(track)
            break
    return redirect('/music')



@app.route('/audio/<path:filename>')
def serve_audio(filename):
    audio_path = 'CompleteAudio/' + filename
    return send_file(audio_path, mimetype='audio/mp3', as_attachment=True)

@app.route('/audioj/<path:filename>')
def serve_audioj(filename):
    audio_path = 'FinalMFIles/' + filename
    return send_file(audio_path, mimetype='audio/mp3', as_attachment=True)

@app.route('/job', methods=['GET'])
def list_jobs():
    return render_template('jobs.html', jobs=jobs)

@app.route('/job/<int:job_id>', methods=['GET'])
def get_job(job_id):
    #sem uso ja se encontra implementado em cima
    """ for job in jobs:
        if job.job_id == job_id:
            return jsonify(job)
    return jsonify({'message': 'Job não encontrado'}) """


@app.route('/reset', methods=['POST'])
def reset_system():
    # reset 
    global music_data
    global music_files
    global music_id_counter
    global job_id_counter
    global jobs
    global jobs_inicialize
    music_data = []
    music_files = {}
    jobs = []
    jobs_inicialize = []
    music_id_counter = 1
    job_id_counter = 1

    # Delete all files in FinalMFIles
    folder = '../cd2023-proj-107854_107476_/FinalMFIles/'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) and not filename.endswith('.txt'):
                os.unlink(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    # Delete all files in CompleteAudio
    folder = '../cd2023-proj-107854_107476_/CompleteAudio/'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) and not filename.endswith('.txt'):
                os.unlink(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    # Delete all files in Input
    folder = '../cd2023-proj-107854_107476_/Input/'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) and not filename.endswith('.txt'):
                os.unlink(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    # Delete all files in tracks
    folder = '../cd2023-proj-107854_107476_/tracks/'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) and not filename.endswith('.txt'):
                os.unlink(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


    #Purge all the queues
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', virtual_host='broker', credentials=credentials))
    channel = connection.channel()
    channel.queue_purge(queue='task_queue')
    channel.queue_purge(queue='return_queue')

    return redirect('/start')


def send_message(data, header):
    executor.submit(send_msg, data, header)


def send_msg(data, header):
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', virtual_host='broker', credentials=credentials, heartbeat=30, socket_timeout=300))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.basic_publish(exchange='', routing_key='task_queue', body=data,
                          properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,headers=header))
    connection.close()


def split_music(music_file, num_pieces):
    audio = AudioSegment.from_file(music_file, format="mp3")
    total_duration = len(audio)

    piece_duration = total_duration // num_pieces

    pieces = []
    for i in range(num_pieces):
        # Calculate start and end timestamps for each piece
        start_time = i * piece_duration
        end_time = start_time + piece_duration

        # Extract the audio segment for the current piece
        piece = audio[start_time:end_time]

        # Export the piece to binary data
        binary_data = io.BytesIO()
        piece.export(binary_data, format='mp3')

        piece_dict = {
            'id': i + 1,
            'data': binary_data.getvalue()
        }

        # Add the dictionary to the list
        pieces.append(piece_dict)

    return pieces

def combine_music_pieces(track, music_id, num_pieces):

    print("Combining music pieces... ")
    combined_audio = AudioSegment.empty()
    output_dir = '../cd2023-proj-107854_107476_/FinalMFIles/'


    for piece_id in range(1, num_pieces + 1):
        current_file_path = output_dir + f"{track}_{music_id}_{piece_id}.mp3"
        # Load the audio segment from the file
        audio_segment = AudioSegment.from_mp3(current_file_path)

        # Append the audio segment to the combined audio
        combined_audio += audio_segment

    # Export the combined audio to a filez
    location = '../cd2023-proj-107854_107476_/CompleteAudio/' + f'{track}_{music_id}.mp3'
    combined_audio.export(location, format="mp3")

def return_message(ch, method, properties, body):
    global music_data
    music_id = properties.headers['music_id']
    piece_id = properties.headers['piece_id']
    track = properties.headers['track']
    print("music_id: ", music_id)
    print("piece_id: ", piece_id)
    print("track: ", track)
    
    job_id = properties.headers['job_id']
    print("job_id: ", job_id)
    size = properties.headers['size_file']
    print("size: ", size)
    time = properties.headers['processed_time']
    print("time: ", time)
    
    link = f'{track}_{music_id}_{piece_id}.mp3'
    mp3_file_path = f'../cd2023-proj-107854_107476_/FinalMFIles/{track}_{music_id}_{piece_id}.mp3'

    job = Job(job_id, music_id, size, time, track, link)
    jobs.append(job)

    # Convert the WAV audio data to AudioSegment
    audio = AudioSegment.from_wav(BytesIO(body))

    # Export the AudioSegment to MP3 format
    audio.export(mp3_file_path, format='mp3')

    selected_instruments = ['Vocals', 'Other', 'Bass', 'Drums']

    for music in music_data:
        if music.music_id == music_id:
            #music.processing_progress += (1/8 * 100)/(len(selected_instruments))#+1)
            music.processing_progress += (1/(music.n_pieces) * 100)/(len(selected_instruments))
            if music.processing_progress > 100-1/(music.n_pieces):
                music.processed = True
                #combine_music_pieces('merged', music_id, 8) changed
                instrument_tracks = []
                for i, instrument in enumerate(selected_instruments):
                    track = {
                        'name': instrument,
                    }
                    instrument_tracks.append(track)
                for track in instrument_tracks:
                    #combine_music_pieces(track['name'], music_id, 8)
                    combine_music_pieces(track['name'], music_id, music.n_pieces)
                #added ----------------------------------------
                merged_audio = None
                for track in music.instrument_tracks:
                    if track["name"] == 'Vocals':
                        audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Vocals_{music.music_id}.mp3')
                        print(" [x]  Got Vocals")
                    if track["name"] == 'Other':
                        audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Other_{music.music_id}.mp3')
                        print(" [x]  Got Other")
                    if track["name"] == 'Bass':
                        audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Bass_{music.music_id}.mp3')
                        print(" [x]  Got Bass")
                    if track["name"] == 'Drums':
                        audio_segment = AudioSegment.from_mp3(f'CompleteAudio/Drums_{music.music_id}.mp3')
                        print(" [x]  Got Drums")
                    if merged_audio is None:
                        merged_audio = audio_segment
                    else:
                        merged_audio = merged_audio.overlay(audio_segment, position=0)
                merged_audio.export(f'CompleteAudio/merged_{music.music_id}.mp3', format='mp3')    
                print(" [x] Done Merging")
                #------------------------------------------------------
            break

    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_server():
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost', virtual_host='broker', credentials=credentials, heartbeat=30,socket_timeout=300))
    channel = connection.channel()
    channel.queue_declare(queue='return_queue', durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue='return_queue', on_message_callback=return_message)
    channel.start_consuming()
    

if __name__ == '__main__':
    executor.submit(app.run)
    executor.submit(start_server())

   
