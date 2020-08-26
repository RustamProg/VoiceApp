# Подключение необходимых библиотек
from tinkoff_voicekit_client import ClientSTT
import logging
import datetime
import psycopg2
import os
import pandas as pd


# Создание класса распознавателя
class RecognizerAndLogger:
    # Инициализация
    def __init__(self, path, ph_num, rec_step, api_k, sec_k):
        self.path = path  # Путь к файлу аудиозаписи
        self.ph_num = ph_num  # Номер телефона (в принципе он здесь лишний, но можно добавить разные условия проверки)
        self.rec_step = rec_step  # Номер этапа
        self.api_k = api_k  # API KEY
        self.sec_k = sec_k  # SECRET KEY

        # Создание логгера
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # Сохранение лога в файл recognizer_logs.log
        logger_handler = logging.FileHandler('recognizer_logs.log')
        logger_handler.setLevel(logging.INFO)

        logger_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logger_handler.setFormatter(logger_formatter)

        self.logger.addHandler(logger_handler)
        self.logger.info('Initializing of recognition class complete')
        # Небольшая проверка работы логгинга
        if len(self.ph_num) != 11:
            self.logger.warning('Wrong type of number')

    # Метод получения всей распознанной информации в виде словаря
    def get_info(self):
        audio_info = self.recognize_audio()  # Вызов метода recognize_audio
        time_now = datetime.datetime.now().strftime("%H:%M")  # Установка времени
        date_now = datetime.datetime.now().strftime("%d/%m/%y")  # Установка даты
        return {
            'date': date_now,
            'time': time_now,
            'result1': audio_info['result1'],
            'result2': audio_info['result2'],
            'ph_num': self.ph_num,
            'duration': audio_info['duration'],
            'text': audio_info['text']
        }
        self.logger.info('Recognition complete, returning information')

    # Непосредственно сам метод распознавания
    def recognize_audio(self):
        # Установка аудио конфигурации для дальнейшего распознавания
        audio_config = {
            "encoding": "LINEAR16",
            "sample_rate_hertz": 8000,
            "num_channels": 1
        }
        # Создание клиента
        client = ClientSTT(self.api_k, self.sec_k)
        # Распознвание аудио
        response = client.recognize(self.path, audio_config)
        negative_words = ['нет', 'неудобно', 'не могу', 'я занят', 'я сейчас занят']  # Список негативных слов
        positive_words = ['да конечно', 'говорите', 'да удобно']  # Список положительных слов
        result1 = ''
        result2 = ''
        resp_text = response[0]['alternatives'][0]['transcript']  # Получение чистого текста аудио

        # Если выбран этап 1 или оба этапа
        if self.rec_step == 1 or self.rec_step == 3:
            # Если это автоответчик
            if resp_text.find('автоответчик') != -1:
                result1 = 0
                self.logger.info(f'Recognized automatic responder in {self.path} file')
            # Если это человек
            else:
                result1 = 1
                self.logger.info(f'Recognized people in {self.path} file')

        # Если выбран этап 2 или оба этапа
        if (self.rec_step == 2 or self.rec_step == 3) and (result1 != 0):
            # Проверка на негативность аудио
            for word in negative_words:
                if resp_text.find(word) != -1:
                    result2 = 0
                    break
            # Проверка на положительность аудио
            for word in positive_words:
                if resp_text.find(word) != -1:
                    result2 = 1
                    break
        # Словарь с распознанной информацией
        info_dict = {
            'result1': result1,
            'result2': result2,
            'duration': response[0]['end_time'],
            'text': resp_text
        }

        return info_dict


API_KEY = '###'  # Нужно ввести API_KEY
SECRET_KEY = '###'  # Нужно ввести SECRET_KEY

# Вод пользователем необходимой информации
path = input('Input path to .wav file: ')
ph_num = str(input('Input phone number: '))
flag = int(input('Input flag (1 - save to DATABASE, 0 - not save): '))
rec_step = int(input('Input step (1 - first step, 2 - second step, 3 - both steps): '))

# Проверка существования лога данных
# Если существует, то чтение файла
if os.path.exists('data_log.txt'):
    df = pd.read_csv('data_log.txt', sep=' ', index_col=0)
# Иначе создание нового датафрейма
else:
    df = pd.DataFrame(columns=[
        'date',
        'time',
        'result_step1',
        'result_step2',
        'phone_number',
        'audio_duration',
        'recognition_result'
    ])

# Распознавание
rec = RecognizerAndLogger(path, ph_num, rec_step, API_KEY, SECRET_KEY)
info = rec.get_info()
df = df.append(info, ignore_index=True)
# Сохранение в лог данных
df.to_csv('data_log.txt',  sep=' ')

# Если нужно сохранить в БД, то сохраняем его
if flag == 1:
    connection = psycopg2.connect(
        database='test1',
        user='postgres',
        password='qwerty12',
        host='127.0.0.1',
        port='5432',
    )
    print('Succesfully connected')
    cur = connection.cursor()
    if info['result1'] == '':
        cur.execute(
            f"INSERT INTO voicetable (date, time, result_step2, phone_number, audio_duration, recognition_result) VALUES ('{info['date']}', '{info['time']}', {info['result2']}, '{info['ph_num']}', '{info['duration']}', '{info['text']}')"
        )
    elif info['result2'] == '':
        cur.execute(
            f"INSERT INTO voicetable (date, time, result_step1, phone_number, audio_duration, recognition_result) VALUES ('{info['date']}', '{info['time']}', {info['result1']}, '{info['ph_num']}', '{info['duration']}', '{info['text']}')"
        )
    else:
        cur.execute(
            f"INSERT INTO voicetable (date, time, result_step1, result_step2, phone_number, audio_duration, recognition_result) VALUES ('{info['date']}', '{info['time']}', {info['result1']}, {info['result2']}, '{info['ph_num']}', '{info['duration']}', '{info['text']}')"
        )

    connection.commit()
    connection.close()


