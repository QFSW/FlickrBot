from datetime import date, datetime, timedelta
from dotenv import load_dotenv
import dateutil.parser
import flickr_api
import glob
import os
import sys
import json
import random
import time

upload_interval = timedelta(hours=3)

auth_file = "auth.txt"
config_path = 'config.json'
db_path = 'flickr_db.json'

def json_serializer(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def flickr_authenticate():
    print('Authenticating')
    load_dotenv()
    flickr_api.set_keys(api_key = os.getenv("API_KEY"), api_secret = os.getenv("API_SECRET"))
    flickr_api.set_auth_handler(auth_file)

def flickr_upload(image, db, config):
    print('Uploading %s to flickr' % image)
    path = os.path.join(config['image_dir'], image)
    upload_time = datetime.now()
    flickr_api.upload(photo_file=path)
    print('Upload complete')

    db['last_upload'] = upload_time
    db['uploaded'].append(image)
    write_db(db, db_path)

def get_images(config):
    for file in os.listdir(config['image_dir']):
        if file.endswith(config['image_ext']):
            yield file

def load_db(path):
    print('Loading DB')
    db = {}
    try:
        f = open(path, 'r')
        db = json.load(f)
        f.close()

    except IOError:
        print('DB missing; creating fresh DB')
    except Exception:
        print('DB corrupt: creating fresh DB')
        db = {}

    if 'last_upload' not in db:
        db['last_upload'] = datetime.now() - upload_interval
    else:
        db['last_upload'] = dateutil.parser.parse(db['last_upload'])
        
    if 'uploaded' not in db:
        db['uploaded'] = []

    return db

def write_db(db, path):
    try:
        f = open(path, 'w')
        json.dump(db, f, default=json_serializer)
        f.close()

    except IOError:
        print('DB could not be written')

def load_config(path):
    print('Loading config')
    try:
        f = open(path, 'r')
        config = byteify(json.load(f))
        f.close()

        if 'image_dir' not in config:
            raise ValueError("Config requires image_dir")
        if 'image_ext' not in config:
            raise ValueError("Config requires image_ext")
        return config

    except IOError:
        raise RuntimeError('Config missing')

def main():
    config = load_config(config_path)
    db = load_db(db_path)
    flickr_authenticate()
    print("Initialization successful")

    while True:
        images = get_images(config)
        new_images = filter(lambda img: img not in db['uploaded'], images)

        while datetime.now() - db['last_upload'] < upload_interval:
            time.sleep(upload_interval.seconds / 4)

        if len(new_images) > 0:
            flickr_upload(random.choice(new_images), db, config)
        else:
            time.sleep(upload_interval.seconds / 4)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()