
import datetime
import logging
import argparse
import subprocess
import os
import pika
import time
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment

# limit the number of thread used by pytorch
import torch
torch.set_num_threads(1)

executor = ThreadPoolExecutor()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


credentials = pika.PlainCredentials('guest','guest')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',virtual_host='broker',credentials=credentials,heartbeat=30,socket_timeout=300))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)
channel.queue_declare(queue='keep_alive_queue')
print(' [*] Waiting for messages. To exit press CTRL+C')


def process_message(ch, method, properties, body):

    print(" [x] Received ")
    inicial_time = datetime.datetime.now().timestamp()
    music_id = properties.headers['music_id']
    piece_id = properties.headers['piece_id']
    selected_instruments = properties.headers['selected_instruments']
    job_id = properties.headers['job_id']
    print("music_id: ", music_id)
    print("piece_id: ", piece_id)
    print("selected_instruments: ", selected_instruments)
    print("job_id: ", job_id)
    
    audio_data = BytesIO(body)
    audio = AudioSegment.from_file(audio_data, format="mp3")

    out = 'tracks'
    location = f"tracks/music_{piece_id}_{music_id}.mp3"
    audio.export(location, format="mp3")

    model = get_model(name='htdemucs')
    model.cpu()
    model.eval()

    # load the audio file
    wav = AudioFile(location).read(streams=0,
    samplerate=model.samplerate, channels=model.audio_channels)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    
    # apply the model
    sources = apply_model(model, wav[None], device='cpu', progress=True, num_workers=1)[0]
    sources = sources * ref.std() + ref.mean()

    # store the model
    for source, name in zip(sources, model.sources):
        stem = f'{out}/{name}_{piece_id}_{music_id}.wav'
        save_audio(source, str(stem), samplerate=model.samplerate)

    size_file = 0

    with open(f'tracks/vocals_{piece_id}_{music_id}.wav', 'rb') as file:
        merged_audio_data = file.read()
    size_file += os.path.getsize(f'tracks/vocals_{piece_id}_{music_id}.wav')
    final_time = datetime.datetime.now().timestamp()
    processed_time = int(final_time - inicial_time)
    message_header = {'music_id': music_id,
                    'piece_id': piece_id,
                    'track': 'Vocals',
                    'job_id': job_id,
                    'size_file': size_file,
                    'processed_time': processed_time,
                    }
    send_message(merged_audio_data, message_header)
    print(" [x] Sent Vocals")

    with open(f'tracks/drums_{piece_id}_{music_id}.wav', 'rb') as file:
        merged_audio_data = file.read()
    size_file += os.path.getsize(f'tracks/drums_{piece_id}_{music_id}.wav')
    final_time = datetime.datetime.now().timestamp()
    processed_time = int(final_time - inicial_time)
    message_header = {'music_id': music_id,
                    'piece_id': piece_id,
                    'track': 'Drums',
                    'job_id': job_id,
                    'size_file': size_file,
                    'processed_time': processed_time,
                    }
    send_message(merged_audio_data, message_header)
    print(" [x] Sent Drums")

    with open(f'tracks/bass_{piece_id}_{music_id}.wav', 'rb') as file:
        merged_audio_data = file.read()
    size_file += os.path.getsize(f'tracks/bass_{piece_id}_{music_id}.wav')
    final_time = datetime.datetime.now().timestamp()
    processed_time = int(final_time - inicial_time)
    message_header = {'music_id': music_id,
                    'piece_id': piece_id,
                    'track': 'Bass',
                    'job_id': job_id,
                    'size_file': size_file,
                    'processed_time': processed_time,
                    }
    send_message(merged_audio_data, message_header)
    print(" [x] Sent Bass")

    with open(f'tracks/other_{piece_id}_{music_id}.wav', 'rb') as file:
        merged_audio_data = file.read()
    size_file += os.path.getsize(f'tracks/other_{piece_id}_{music_id}.wav')
    final_time = datetime.datetime.now().timestamp()
    processed_time = int(final_time - inicial_time)
    message_header = {'music_id': music_id,
                        'piece_id': piece_id,
                        'track': 'Other',
                        'job_id': job_id,
                        'size_file': size_file,
                        'processed_time': processed_time,
                        }    
    send_message(merged_audio_data, message_header)
    print(" [x] Sent Other")

    merged_audio = None
    
    # load the vocals and drums to merge them       Changed !!!!!
    """ for i in selected_instruments:
        if i["name"] == 'Vocals':
            audio_segment = AudioSegment.from_wav('tracks/vocals.wav')
            
        elif i["name"] == 'Drums':
            audio_segment = AudioSegment.from_wav('tracks/drums.wav')
        elif i["name"] == 'Bass':
            audio_segment = AudioSegment.from_wav('tracks/bass.wav')
            
        elif i["name"] == 'Other':
            audio_segment = AudioSegment.from_wav('tracks/other.wav')
            
        if merged_audio is None:
            merged_audio = audio_segment
        else:
            merged_audio = merged_audio.overlay(audio_segment, position=0)

    if merged_audio is not None:
        merged_audio.export('tracks/merged.wav', format='wav')    
        print(" [x] Done Merging")

        with open('tracks/merged.wav', 'rb') as file:
            merged_audio_data = file.read()
        
        size_file += os.path.getsize('tracks/merged.wav')


        final_time = datetime.datetime.now().timestamp()
        processed_time = int(final_time - inicial_time)
        #print(" [x] Time spent processing the message: ", final_time - inicial_time)

        message_header = {'music_id': music_id,
                        'piece_id': piece_id,
                        'track': 'merged',
                        'job_id': job_id,
                        'size_file': size_file,
                        'processed_time': processed_time,
                        }
        
        send_message(merged_audio_data, message_header)
        print(" [x] Sent Merged") """
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback(ch,method, properties, body):
    executor.submit(process_message(ch, method, properties, body))

def send_message(data,header):
    executor.submit(send_msg(data, header))

def send_msg(data,header):
    stream = BytesIO(data)
    stream.seek(0)
    channel.queue_declare(queue='return_queue', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='return_queue',
        body=stream.read(),
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
            headers=header
        )
    )

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='task_queue', on_message_callback=callback)
channel.start_consuming()
connection.close()